//! Software updates (model.py: checkSoftwareUpdated, listAvailableReleases, updateSoftware /
//! updateCudaSoftware and their helpers; config.py: setupDownloadUrl, _channelForVersion) and the
//! version comparison they use (packaging.version, PEP 440).
use crate::net::Http;
use anyhow::{bail, Result};
use serde_json::Value;
use std::cmp::Ordering;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::time::Duration;

const GITHUB_URL: &str = "https://api.github.com/repos/misyaguziya/VRCT/releases/latest";
const GITHUB_RELEASES_LIST_URL: &str = "https://api.github.com/repos/misyaguziya/VRCT/releases";
const MIN_SUPPORTED_VERSION: &str = "3.4.3";
const HF_REPO_STABLE: &str = "ms-software/VRCT";
const HF_REPO_BETA: &str = "ms-software/VRCT-beta";
/// model._HTTP_TIMEOUT (connect 10 s, read 60 s)
const HTTP_TIMEOUT: Duration = Duration::from_secs(60);
const SETUP_NAME: &str = "VRCT_setup.exe";
const SHA256_SIDECAR_ATTEMPTS: usize = 3;

// ---- PEP 440 (packaging.version) ------------------------------------------------------------

/// packaging.version.Version, compared by its _cmpkey
#[derive(Clone, Debug)]
pub struct Version {
    epoch: u64,
    release: Vec<u64>,
    pre: Option<(u8, u64)>, // 0 a, 1 b, 2 rc
    post: Option<u64>,
    dev: Option<u64>,
    local: Option<Vec<LocalPart>>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum LocalPart {
    Num(u64),
    Text(String),
}

fn version_regex() -> &'static regex::Regex {
    static RE: OnceLock<regex::Regex> = OnceLock::new();
    RE.get_or_init(|| {
        regex::Regex::new(r"(?ix)^\s*v?
            (?:(?P<epoch>[0-9]+)!)?
            (?P<release>[0-9]+(?:\.[0-9]+)*)
            (?P<pre>[-_\.]?(?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)[-_\.]?(?P<pre_n>[0-9]+)?)?
            (?P<post>(?:-(?P<post_n1>[0-9]+))|(?:[-_\.]?(?P<post_l>post|rev|r)[-_\.]?(?P<post_n2>[0-9]+)?))?
            (?P<dev>[-_\.]?(?P<dev_l>dev)[-_\.]?(?P<dev_n>[0-9]+)?)?
            (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?
            \s*$").unwrap()
    })
}

impl Version {
    /// packaging.version.parse (None for InvalidVersion)
    pub fn parse(s: &str) -> Option<Version> {
        let c = version_regex().captures(s)?;
        let num = |name: &str| c.name(name).map(|m| m.as_str().parse::<u64>().unwrap_or(u64::MAX));
        let pre = c.name("pre_l").map(|l| {
            let kind = match l.as_str().to_lowercase().as_str() {
                "alpha" | "a" => 0,
                "beta" | "b" => 1,
                _ => 2, // c, pre, preview, rc
            };
            (kind, num("pre_n").unwrap_or(0))
        });
        let post = c.name("post").map(|_| num("post_n1").or(num("post_n2")).unwrap_or(0));
        let dev = c.name("dev").map(|_| num("dev_n").unwrap_or(0));
        let local = c.name("local").map(|m| {
            m.as_str()
                .split(['-', '_', '.'])
                .map(|p| match p.parse::<u64>() {
                    Ok(n) if p.bytes().all(|b| b.is_ascii_digit()) => LocalPart::Num(n),
                    _ => LocalPart::Text(p.to_lowercase()),
                })
                .collect()
        });
        Some(Version {
            epoch: num("epoch").unwrap_or(0),
            release: c["release"].split('.').map(|p| p.parse().unwrap_or(u64::MAX)).collect(),
            pre,
            post,
            dev,
            local,
        })
    }

    fn release_key(&self) -> &[u64] {
        let mut end = self.release.len();
        while end > 0 && self.release[end - 1] == 0 {
            end -= 1;
        }
        &self.release[..end]
    }
}

/// -inf / value / +inf for the optional parts of _cmpkey
#[derive(PartialEq, Eq, PartialOrd, Ord)]
enum Bound<T: Ord> {
    NegInf,
    Value(T),
    PosInf,
}

impl Version {
    fn key(&self) -> (u64, &[u64], Bound<(u8, u64)>, Bound<u64>, Bound<u64>, Bound<Vec<(Bound<u64>, String)>>) {
        let pre = match (self.pre, self.post, self.dev) {
            (None, None, Some(_)) => Bound::NegInf,
            (None, _, _) => Bound::PosInf,
            (Some(p), _, _) => Bound::Value(p),
        };
        let post = self.post.map_or(Bound::NegInf, Bound::Value);
        let dev = self.dev.map_or(Bound::PosInf, Bound::Value);
        let local = match &self.local {
            None => Bound::NegInf,
            Some(parts) => Bound::Value(parts.iter().map(|p| match p {
                LocalPart::Num(n) => (Bound::Value(*n), String::new()),
                LocalPart::Text(t) => (Bound::NegInf, t.clone()),
            }).collect()),
        };
        (self.epoch, self.release_key(), pre, post, dev, local)
    }
}

impl PartialEq for Version {
    fn eq(&self, other: &Self) -> bool {
        self.key() == other.key()
    }
}

impl PartialOrd for Version {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.key().cmp(&other.key()))
    }
}

/// Model._isVersionSupported
pub fn is_version_supported(version: &str) -> bool {
    match (Version::parse(version), Version::parse(MIN_SUPPORTED_VERSION)) {
        (Some(v), Some(min)) => v >= min,
        _ => false,
    }
}

/// Config._channelForVersion: "-beta" / "-rc" in the version means the beta channel
pub fn channel_for_version(version: &str) -> &'static str {
    if version.contains("-beta") || version.contains("-rc") { "beta" } else { "stable" }
}

// ---- releases ------------------------------------------------------------------------------

/// The settings the updater reads from config
#[derive(Clone, Debug)]
pub struct Settings {
    pub channel: String,
    pub version: String,
    pub ui_language: String,
    /// config.PATH_LOCAL: where VRCT_setup.exe is written and started
    pub path_local: PathBuf,
}

#[derive(Clone, Debug, PartialEq)]
pub struct ReleaseInfo {
    pub tag: String,
    pub version: String,
    pub is_prerelease: bool,
    pub published_at: String,
}

/// The outcomes of updateSoftware (the app quits on success)
pub const SETUP_LAUNCHED: &str = "launched";
pub const SETUP_DOWNLOAD_FAILED: &str = "download_failed";
pub const SETUP_VERIFY_FAILED: &str = "verify_failed";

/// Python's str(value) for the published_at field
fn py_str(v: Option<&Value>) -> String {
    match v {
        None => String::new(),
        Some(Value::String(s)) => s.clone(),
        Some(Value::Null) => "None".into(),
        Some(Value::Bool(b)) => if *b { "True" } else { "False" }.into(),
        Some(other) => other.to_string(),
    }
}

/// Python's truthiness for r.get("prerelease", False)
fn truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => n.as_f64() != Some(0.0),
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

pub struct Updater<'a> {
    pub http: &'a Http,
    pub settings: Settings,
    /// Log lines (printLog) for the UI's log
    pub log: &'a dyn Fn(&str),
}

impl Updater<'_> {
    fn get_json(&self, url: &str) -> Result<Value> {
        let response = self.http.get(url, &[], Some(HTTP_TIMEOUT))?;
        if !response.status().is_success() {
            bail!("HTTP {}", response.status());
        }
        Ok(response.json()?)
    }

    /// _fetchGithubReleases: all releases but drafts (objects only), newest first
    fn fetch_releases(&self) -> Result<Vec<Value>> {
        let releases = self.get_json(GITHUB_RELEASES_LIST_URL)?;
        let Some(list) = releases.as_array() else { return Ok(vec![]) };
        Ok(list.iter().filter(|r| r.is_object() && !truthy(r.get("draft"))).cloned().collect())
    }

    fn beta_candidates(&self) -> Result<Vec<Value>> {
        Ok(self
            .fetch_releases()?
            .into_iter()
            .filter(|r| r.get("name").and_then(Value::as_str).is_some_and(is_version_supported) && truthy(r.get("prerelease")))
            .collect())
    }

    /// checkSoftwareUpdated: (is_update_available, new_version); new_version is None when no
    /// beta release qualifies, or the latest release has no name
    pub fn check_software_updated(&self) -> (bool, Option<Value>) {
        let version: Result<Option<Value>> = (|| {
            if self.settings.channel == "beta" {
                Ok(self.beta_candidates()?.first().and_then(|r| r.get("name").cloned()))
            } else {
                let latest = self.http.get(GITHUB_URL, &[], Some(HTTP_TIMEOUT))?.json::<Value>()?;
                Ok(latest.get("name").cloned())
            }
        })();
        let version = match version {
            Ok(v) => v,
            Err(_) => return (false, Some(Value::String(String::new()))),
        };
        let update = match version.as_ref().and_then(Value::as_str) {
            Some(v) => match (Version::parse(v), Version::parse(&self.settings.version)) {
                (Some(new), Some(current)) => new > current,
                _ => false, // InvalidVersion is caught (errorLogging) and update_flag stays False
            },
            None => false,
        };
        (update, version)
    }

    /// listAvailableReleases
    pub fn list_available_releases(&self) -> Vec<ReleaseInfo> {
        let Ok(releases) = self.fetch_releases() else { return vec![] };
        releases
            .iter()
            .filter_map(|r| {
                let version = r.get("name")?.as_str()?;
                let tag = r.get("tag_name")?.as_str()?;
                is_version_supported(version).then(|| ReleaseInfo {
                    tag: tag.to_string(),
                    version: version.to_string(),
                    is_prerelease: truthy(r.get("prerelease")),
                    published_at: py_str(r.get("published_at")),
                })
            })
            .collect()
    }

    /// config.setupDownloadUrl(target_version, tag)
    fn setup_download_url(&self, target_version: Option<&str>, tag: Option<&str>) -> String {
        let channel = target_version.map(channel_for_version).unwrap_or(&self.settings.channel);
        let repo = if channel == "beta" { HF_REPO_BETA } else { HF_REPO_STABLE };
        format!("https://huggingface.co/{repo}/resolve/{}/{SETUP_NAME}", tag.unwrap_or("main"))
    }

    /// _resolveReleaseForVersion
    fn resolve_release(&self, target_version: Option<&str>) -> Option<Value> {
        let result: Result<Option<Value>> = (|| {
            if let Some(target) = target_version {
                return Ok(self.fetch_releases()?.into_iter().find(|r| r.get("name").and_then(Value::as_str) == Some(target)));
            }
            if self.settings.channel == "beta" {
                return Ok(self.beta_candidates()?.into_iter().next());
            }
            let data = self.get_json(GITHUB_URL)?;
            Ok(data.is_object().then_some(data))
        })();
        result.ok().flatten()
    }

    /// _fetchSha256Digest: the first word of the sidecar, lowercased, when it is 64 hex digits
    fn fetch_sha256_digest(&self, url: &str) -> Option<String> {
        for _ in 0..SHA256_SIDECAR_ATTEMPTS {
            let Ok(text) = self.http.get(url, &[], Some(HTTP_TIMEOUT)).and_then(|r| {
                if !r.status().is_success() {
                    bail!("HTTP {}", r.status());
                }
                Ok(r.text()?)
            }) else { continue };
            let digest = crate::pyfmt::strip(&text).split(crate::pyfmt::isspace).find(|s| !s.is_empty()).unwrap_or("").to_lowercase();
            if digest.len() == 64 && digest.bytes().all(|b| b.is_ascii_hexdigit()) {
                return Some(digest);
            }
        }
        None
    }

    /// _fetchExpectedSha256: Ok(None) without a ".sha256" asset, Err when one exists but none of
    /// them gave a digest (SetupSha256Unavailable)
    fn fetch_expected_sha256(&self, release: Option<&Value>) -> Result<Option<String>, ()> {
        let Some(assets) = release.and_then(|r| r.get("assets")).and_then(Value::as_array) else { return Ok(None) };
        let urls: Vec<&str> = assets
            .iter()
            .filter(|a| a.get("name").and_then(Value::as_str).is_some_and(|n| n.ends_with(".sha256")))
            .filter_map(|a| a.get("browser_download_url").and_then(Value::as_str))
            .collect();
        if urls.is_empty() {
            return Ok(None);
        }
        urls.iter().find_map(|u| self.fetch_sha256_digest(u)).map(Some).ok_or(())
    }

    fn setup_path(&self) -> PathBuf {
        self.settings.path_local.join(SETUP_NAME)
    }

    /// _downloadSetup: up to 5 attempts; None when the file is in place
    fn download_setup(&self, expected: Option<&str>, url: &str) -> Option<&'static str> {
        let dest = self.setup_path();
        for _ in 0..5 {
            let attempt = (|| -> Result<Option<&'static str>> {
                let mut response = self.http.get(url, &[], Some(HTTP_TIMEOUT))?;
                if !response.status().is_success() {
                    bail!("HTTP {}", response.status());
                }
                let mut file = std::fs::File::create(&dest)?;
                let mut hasher = Sha256::new();
                let mut size = 0usize;
                let mut buf = vec![0u8; 1024 * 5];
                loop {
                    let n = response.read(&mut buf)?;
                    if n == 0 {
                        break;
                    }
                    file.write_all(&buf[..n])?;
                    hasher.update(&buf[..n]);
                    size += n;
                }
                drop(file);
                if size < 1024 * 1024 {
                    bail!("Downloaded setup file is too small ({size} bytes); likely not a valid installer");
                }
                if let Some(expected) = expected {
                    let actual: String = hasher.finalize().iter().map(|b| format!("{b:02x}")).collect();
                    if actual != expected {
                        (self.log)(&format!("Setup file SHA-256 mismatch: expected {expected}, got {actual}. Aborting update."));
                        let _ = std::fs::remove_file(&dest);
                        return Ok(Some(SETUP_VERIFY_FAILED));
                    }
                }
                Ok(None)
            })();
            match attempt {
                Ok(r) => return r,
                Err(_) => {
                    let _ = std::fs::remove_file(&dest);
                }
            }
        }
        Some(SETUP_DOWNLOAD_FAILED)
    }

    /// _downloadVerifiedSetup
    fn download_verified_setup(&self, target_version: Option<&str>) -> Option<&'static str> {
        let release = self.resolve_release(target_version);
        let what = target_version.unwrap_or("the latest release");
        let expected = match self.fetch_expected_sha256(release.as_ref()) {
            Ok(e) => e,
            Err(()) => {
                (self.log)(&format!("Setup file SHA-256 sidecar was published for {what} but could not be retrieved; \
                                     aborting update (not falling back to size-only validation)"));
                return Some(SETUP_VERIFY_FAILED);
            }
        };
        if expected.is_none() {
            (self.log)(&format!("Setup file SHA-256 could not be verified (no .sha256 asset found for {what}); \
                                 falling back to size-only validation"));
        }
        let mut urls = vec![self.setup_download_url(None, None)];
        if let Some(target) = target_version {
            let tag = release.as_ref().and_then(|r| r.get("tag_name")).and_then(Value::as_str)
                .filter(|t| !t.is_empty()).map(String::from).unwrap_or(format!("v{target}"));
            urls = vec![self.setup_download_url(Some(target), Some(&tag))];
            if expected.is_none() {
                urls.push(self.setup_download_url(Some(target), None));
            }
        }
        let mut failure = Some(SETUP_DOWNLOAD_FAILED);
        for url in urls {
            failure = self.download_setup(expected.as_deref(), &url);
            if failure != Some(SETUP_DOWNLOAD_FAILED) {
                return failure;
            }
        }
        failure
    }

    /// _updateAndRestart(edition, target_version): download and verify the installer, then
    /// `launch(args, cwd)` it (the caller quits the app). Returns one of the SETUP_* outcomes.
    pub fn update(&self, edition: &str, target_version: Option<&str>, launch: &dyn Fn(&[String], &Path)) -> &'static str {
        if target_version.is_some_and(|v| !is_version_supported(v)) {
            return SETUP_DOWNLOAD_FAILED;
        }
        if let Some(failure) = self.download_verified_setup(target_version) {
            return failure;
        }
        let channel = target_version.map(channel_for_version).unwrap_or(&self.settings.channel).to_string();
        let mut args = vec![SETUP_NAME.to_string(), format!("/EDITION={edition}"),
                            format!("/UILANG={}", self.settings.ui_language), format!("/CHANNEL={channel}")];
        if let Some(target) = target_version {
            args.push(format!("/VERSION={target}"));
        }
        launch(&args, &self.settings.path_local);
        SETUP_LAUNCHED
    }
}
