//! The keyboard dictionaries' download (ime_data::prepare) against a local server serving
//! GitHub-like archives: only the files listed, checked by SHA-256; the set ready once whole.
mod support;

use sha2::{Digest, Sha256};
use std::io::Write;
use std::path::Path;
use std::sync::{Arc, Mutex};
use support::Mock;
use vrct_backend::ime_data::{self, Source};
use vrct_backend::net::Http;

fn leak(s: String) -> &'static str {
    Box::leak(s.into_boxed_str())
}

/// A zip as GitHub serves it: everything under "<project>-<commit>/"
fn archive(project: &str, commit: &str, files: &[(&str, &[u8])]) -> Vec<u8> {
    let mut zip = zip::ZipWriter::new(std::io::Cursor::new(vec![]));
    let options = zip::write::SimpleFileOptions::default();
    for (name, data) in files {
        zip.start_file(format!("{project}-{commit}/{name}"), options).unwrap();
        zip.write_all(data).unwrap();
    }
    zip.finish().unwrap().into_inner()
}

fn hash(data: &[u8]) -> &'static str {
    leak(format!("{:x}", Sha256::digest(data)))
}

struct Server {
    mock: Mock,
    served: Arc<Mutex<Vec<String>>>,
}

/// Serves the projects' archives at codeload's paths
fn serve(projects: Vec<(&'static str, &'static str, Vec<u8>)>) -> Server {
    let served = Arc::new(Mutex::new(vec![]));
    let log = served.clone();
    let mock = Mock::start(Box::new(move |request| {
        let url = request["url"].as_str().unwrap_or_default().to_string();
        log.lock().unwrap().push(url.clone());
        match projects.iter().find(|(repo, commit, _)| url.ends_with(&format!("/{repo}/zip/{commit}"))) {
            Some((_, _, zip)) => (200, vec![("content-type", "application/zip".into())], zip.clone()),
            None => (404, vec![], b"not found".to_vec()),
        }
    }));
    Server { mock, served }
}

fn opencc(dir: &Path) -> std::path::PathBuf {
    let d = dir.join("opencc-src");
    std::fs::create_dir_all(&d).unwrap();
    std::fs::write(d.join("t2s.json"), "{}").unwrap();
    d
}

fn temp(name: &str) -> std::path::PathBuf {
    let d = std::env::temp_dir().join(format!("vrct-ime-data-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d
}

#[test]
fn the_listed_files_are_taken_checked_and_set_up_once() {
    let schema = b"schema: {schema_id: demo}\n".as_slice();
    let license = b"Apache License".as_slice();
    let zip_a = archive("rime-demo", "aaaa", &[("demo.schema.yaml", schema), ("LICENSE", license), ("README.md", b"not taken")]);
    let zip_b = archive("rime-other", "bbbb", &[("other.dict.yaml", b"dict"), ("LICENSE", b"LGPL")]);
    let sources = vec![
        Source { repo: "someone/rime-demo", commit: "aaaa", size: zip_a.len() as u64,
                 files: leak_files(vec![("demo.schema.yaml", hash(schema)), ("LICENSE", hash(license))]) },
        Source { repo: "rime/rime-other", commit: "bbbb", size: 3 * zip_a.len() as u64,
                 files: leak_files(vec![("other.dict.yaml", hash(b"dict")), ("LICENSE", hash(b"LGPL"))]) },
    ];
    let server = serve(vec![("someone/rime-demo", "aaaa", zip_a), ("rime/rime-other", "bbbb", zip_b)]);
    let http = Http::redirected(&server.mock.root).unwrap();
    let root = temp("ok");
    // a stopped earlier run (no marker) and an older build's folder: made again, cleaned away
    std::fs::create_dir_all(ime_data::shared_dir(&root)).unwrap();
    std::fs::write(ime_data::shared_dir(&root).join("stale.yaml"), "x").unwrap();
    std::fs::create_dir_all(root.join("ime").join("shared.part")).unwrap();
    let steps = Mutex::new(vec![]);
    ime_data::prepare(&http, &root, &sources, ime_data::GITHUB_ARCHIVES, &opencc(&root), &|p| steps.lock().unwrap().push(p), &|_, _| {}).unwrap();

    let shared = ime_data::shared_dir(&root);
    assert_eq!(std::fs::read(shared.join("demo.schema.yaml")).unwrap(), schema);
    assert_eq!(std::fs::read(shared.join("other.dict.yaml")).unwrap(), b"dict");
    assert_eq!(std::fs::read(shared.join("licenses").join("rime-demo.txt")).unwrap(), license);
    assert!(shared.join("opencc").join("t2s.json").is_file());
    assert!(!shared.join("README.md").exists() && !shared.join("stale.yaml").exists());
    assert!(!root.join("ime").join("shared.part").exists() && !root.join("ime").join("download").exists());
    assert!(ime_data::ready(&root, &sources));
    // by the archives' sizes: the first is a quarter of all
    let steps = steps.lock().unwrap().clone();
    assert!(steps.windows(2).all(|w| w[0] <= w[1]) && steps.contains(&0.25) && steps.last() == Some(&1.0), "{steps:?}");
    assert_eq!(server.served.lock().unwrap().len(), 2);
    // there already: nothing is downloaded again
    ime_data::prepare(&http, &root, &sources, ime_data::GITHUB_ARCHIVES, &opencc(&root), &|_| {}, &|_, _| {}).unwrap();
    assert_eq!(server.served.lock().unwrap().len(), 2);
    // another commit: set up again
    let newer = vec![Source { repo: "someone/rime-demo", commit: "aaab", size: 1, files: sources[0].files }];
    assert!(!ime_data::ready(&root, &newer));
    let _ = std::fs::remove_dir_all(&root);
}

fn leak_files(v: Vec<(&'static str, &'static str)>) -> &'static [(&'static str, &'static str)] {
    Box::leak(v.into_boxed_slice())
}

#[test]
fn a_file_that_does_not_match_its_hash_sets_nothing_up() {
    let zip = archive("rime-demo", "aaaa", &[("demo.schema.yaml", b"changed")]);
    let sources = vec![Source { repo: "someone/rime-demo", commit: "aaaa", size: 1, files: leak_files(vec![("demo.schema.yaml", hash(b"original"))]) }];
    let server = serve(vec![("someone/rime-demo", "aaaa", zip)]);
    let http = Http::redirected(&server.mock.root).unwrap();
    let root = temp("bad");
    let error = ime_data::prepare(&http, &root, &sources, ime_data::GITHUB_ARCHIVES, &opencc(&root), &|_| {}, &|_, _| {}).unwrap_err();
    assert!(format!("{error:#}").contains("sha256"), "{error:#}");
    assert!(!ime_data::ready(&root, &sources));
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn a_missing_archive_fails_without_setting_up() {
    let sources = vec![Source { repo: "someone/rime-gone", commit: "cccc", size: 1, files: leak_files(vec![("x.yaml", hash(b"x"))]) }];
    let server = serve(vec![]);
    let http = Http::redirected(&server.mock.root).unwrap();
    let root = temp("missing");
    assert!(ime_data::prepare(&http, &root, &sources, ime_data::GITHUB_ARCHIVES, &opencc(&root), &|_| {}, &|_, _| {}).is_err());
    assert!(!ime_data::ready(&root, &sources));
    let _ = std::fs::remove_dir_all(&root);
}

/// The real sources from GitHub (~28 MB), then RIME on them: run by hand with
/// `cargo test -p vrct-backend --test ime_data -- --ignored` and VRCT_RIME_DLL / VRCT_RIME_OPENCC
#[test]
#[ignore]
fn the_real_sources_download_and_convert() {
    let (Some(dll), Some(opencc_dir)) = (std::env::var_os("VRCT_RIME_DLL"), std::env::var_os("VRCT_RIME_OPENCC")) else {
        panic!("set VRCT_RIME_DLL (rime.dll) and VRCT_RIME_OPENCC (_internal/rime/opencc)");
    };
    let root = temp("real");
    let http = Http::new().unwrap();
    let started = std::time::Instant::now();
    ime_data::prepare(&http, &root, ime_data::SOURCES, ime_data::GITHUB_ARCHIVES, Path::new(&opencc_dir), &|_| {},
                      &|m, u| eprintln!("{m} {u}")).unwrap();
    eprintln!("downloaded in {:?}", started.elapsed());
    let user = root.join("ime").join("user");
    std::fs::create_dir_all(&user).unwrap();
    std::fs::write(user.join("default.custom.yaml"), "patch:\n  schema_list:\n    - schema: jaroomaji\n    - schema: luna_pinyin\n").unwrap();
    let rime = vrct_ime::rime::Rime::load(Path::new(&dll)).unwrap();
    rime.start(&ime_data::shared_dir(&root), &user, &user).unwrap();
    let started = std::time::Instant::now();
    assert!(rime.deploy(true));
    eprintln!("deployed in {:?}", started.elapsed());
    let s = rime.session().unwrap();
    assert!(s.select_schema("jaroomaji"));
    s.set_option("ascii_mode", false);
    for k in "nihongo".chars() {
        s.key(k as i32, 0);
    }
    assert_eq!(s.context().candidates[0], "日本語");
    assert!(s.select_schema("luna_pinyin"));
    s.set_option("ascii_mode", false);
    s.set_option("zh_hans", true);
    for k in "xiexie".chars() {
        s.key(k as i32, 0);
    }
    assert_eq!(s.context().candidates[0], "谢谢");
    drop(s);
    let _ = std::fs::remove_dir_all(&root);
}
