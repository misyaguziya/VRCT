// Copyright (c) 2026 misyaguziya. Licensed for use in VRCT only; see LICENSE.
use std::sync::Mutex;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use obfstr::obfstr;
use serde_json::Value;

use crate::{client, json_ok, languages, lock, send, Backend, Res, Table};

// Refresh the token this long before it expires so a request started just
// under the wire does not race the expiry.
const EXPIRY_MARGIN_MS: f64 = 60_000.0;

const LANG_MAP: Table = &[
    ("iw", "he"),
    ("mn", "mn-Cyrl"),
    ("no", "nb"),
    ("otl", "otq"),
    ("sr", "sr-Cyrl"),
    ("tl", "fil"),
    ("tlh", "tlh-Latn"),
    ("zh", "zh-Hans"),
    ("zh-CN", "zh-Hans"),
    ("zh-TW", "zh-Hant"),
];

#[derive(Clone, Debug)]
struct Creds {
    ig: String,
    iid: String,
    key: String,
    token: String,
    expires_at_ms: f64,
}

/// Credentials plus a request counter, shared by every thread.
#[derive(Default)]
struct CredState {
    creds: Option<Creds>,
    sequence: u64,
    generation: u64,
}

#[derive(Default)]
struct CredCache(Mutex<CredState>);

impl CredCache {
    // `fetch` runs under the lock, so other threads wait out one
    // page GET per hour (or per token error). Move it out of the lock if
    // that contention ever shows up.
    fn acquire(
        &self,
        rejected_generation: Option<u64>,
        now_ms: impl FnOnce() -> f64,
        fetch: impl FnOnce() -> Res<Creds>,
    ) -> Res<(Creds, u64, u64)> {
        let mut g = lock(&self.0);
        let stale = g.creds.as_ref().is_none_or(|c| now_ms() >= c.expires_at_ms);
        // A concurrent request may already have replaced the rejected token.
        if stale || rejected_generation == Some(g.generation) {
            g.creds = Some(fetch()?);
            g.generation += 1;
        }
        g.sequence += 1;
        let creds = g.creds.clone().expect("credentials were just stored");
        Ok((creds, g.sequence, g.generation))
    }
}

#[derive(Default)]
pub struct BingEngine {
    creds: CredCache,
}

fn now_ms() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0.0, |d| d.as_secs_f64() * 1000.0)
}

impl Backend for BingEngine {
    fn lang_map(&self) -> Table {
        LANG_MAP
    }
    fn languages(&self) -> Table {
        languages::BING
    }
    fn auto_code(&self) -> &'static str {
        "auto-detect"
    }

    fn translate(&self, text: &str, src: &str, tgt: &str, timeout: Duration) -> Res<String> {
        // One retry: a token can expire (or be revoked) between the cache
        // check and the request landing at Bing.
        let mut rejected_generation = None;
        for attempt in 0..2 {
            let (c, seq, generation) = self
                .creds
                .acquire(rejected_generation, now_ms, || fetch_credentials(timeout))?;
            let rb = client()?
                .post(obfstr!("https://www.bing.com/ttranslatev3"))
                .query(&[
                    (obfstr!("isVertical"), obfstr!("1")),
                    (obfstr!("IG"), c.ig.as_str()),
                    (obfstr!("IID"), format!("{}.{seq}", c.iid).as_str()),
                ])
                .form(&[
                    ("text", text),
                    (obfstr!("fromLang"), src),
                    ("to", tgt),
                    ("token", c.token.as_str()),
                    ("key", c.key.as_str()),
                ])
                .header("Referer", obfstr!("https://www.bing.com/translator"));
            let data = json_ok("Bing", &send("bing.translate", rb, timeout)?)?;
            match parse_translation(&data)? {
                Parsed::Text(t) => return Ok(t),
                Parsed::ApiError(_) if attempt == 0 => {
                    rejected_generation = Some(generation);
                    continue;
                }
                Parsed::ApiError(msg) => return Err(msg),
            }
        }
        Err("Bing: translation failed after refreshing the token".to_owned())
    }
}

fn fetch_credentials(timeout: Duration) -> Res<Creds> {
    let rb = client()?.get(obfstr!("https://www.bing.com/translator"));
    let r = send("bing.credentials", rb, timeout)?;
    if r.status != 200 {
        return Err(format!(
            "Bing: could not load the translator page (HTTP {})",
            r.status
        ));
    }
    parse_page(&r.body)
}

fn is_word(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

/// Text after `prefix` made of `ok` chars and followed by `"`; first
/// occurrence of `prefix` that fits wins.
fn quoted_after<'a>(html: &'a str, prefix: &str, ok: impl Fn(char) -> bool) -> Option<&'a str> {
    html.match_indices(prefix).find_map(|(i, _)| {
        let rest = &html[i + prefix.len()..];
        let end = rest.find(|c| !ok(c))?;
        (end > 0 && rest[end..].starts_with('"')).then(|| &rest[..end])
    })
}

/// `[key, "token", lifetime]` out of `params_AbusePreventionHelper = [...]`.
fn abuse_params(html: &str) -> Option<&str> {
    obfstr!(let name = "params_AbusePreventionHelper";);
    html.match_indices(name).find_map(|(i, _)| {
        let rest = html[i + name.len()..].trim_start().strip_prefix('=')?;
        let rest = rest.trim_start().strip_prefix('[')?;
        let end = rest.find(']')?;
        (end > 0).then(|| &rest[..end])
    })
}

fn parse_page(html: &str) -> Res<Creds> {
    let missing = || {
        "Bing: the translator page no longer contains the expected IG/IID/anti-abuse parameters"
            .to_owned()
    };
    let ig = quoted_after(html, obfstr!("IG:\""), is_word).ok_or_else(missing)?;
    let iid = quoted_after(html, obfstr!("data-iid=\""), |c| is_word(c) || c == '.')
        .ok_or_else(missing)?;
    let params = abuse_params(html).ok_or_else(missing)?;

    let parts: Vec<&str> = params
        .splitn(3, ',')
        .map(|p| p.trim().trim_matches('"'))
        .collect();
    let [key, token, lifetime] = parts[..] else {
        return Err(missing());
    };
    let number = |s: &str| s.parse::<f64>().map_err(|_| missing());
    Ok(Creds {
        ig: ig.to_owned(),
        iid: iid.to_owned(),
        key: key.to_owned(),
        token: token.to_owned(),
        // `key` is the issue time in ms, `lifetime` how long it lasts.
        expires_at_ms: number(key)? + number(lifetime)? - EXPIRY_MARGIN_MS,
    })
}

#[derive(Debug, PartialEq)]
enum Parsed {
    Text(String),
    /// Bing reports failures as HTTP 200 with an error object.
    ApiError(String),
}

fn parse_translation(data: &Value) -> Res<Parsed> {
    if let Some(obj) = data.as_object() {
        let detail = match obj.get("errorMessage").and_then(Value::as_str) {
            Some(m) if !m.is_empty() => m.to_owned(),
            _ => data.to_string(),
        };
        let status = obj
            .get("statusCode")
            .map_or("None".to_owned(), Value::to_string);
        return Ok(Parsed::ApiError(format!(
            "Bing: {detail} (statusCode={status})"
        )));
    }
    data.pointer("/0/translations/0/text")
        .and_then(Value::as_str)
        .map(|t| Parsed::Text(t.to_owned()))
        .ok_or_else(|| {
            format!(
                "Bing: unexpected response: {}",
                crate::head(&data.to_string())
            )
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_http::{form, response, scripted};
    use serde_json::json;
    use std::sync::atomic::{AtomicUsize, Ordering};

    fn page(issued: u64, lifetime: u64) -> String {
        format!(
            r#"var IG:"ABC123"; <div data-iid="translator.5025"> var params_AbusePreventionHelper = [{issued},"tok-1",{lifetime}];"#
        )
    }

    fn creds(expires_at_ms: f64) -> Creds {
        Creds {
            ig: "IG".into(),
            iid: "iid".into(),
            key: "1".into(),
            token: "t".into(),
            expires_at_ms,
        }
    }

    #[test]
    fn scrapes_the_page() {
        let c = parse_page(&page(1_000_000, 3_600_000)).unwrap();
        assert_eq!(
            (c.ig.as_str(), c.iid.as_str()),
            ("ABC123", "translator.5025")
        );
        assert_eq!((c.key.as_str(), c.token.as_str()), ("1000000", "tok-1"));
        assert_eq!(
            c.expires_at_ms,
            1_000_000.0 + 3_600_000.0 - EXPIRY_MARGIN_MS
        );
    }

    #[test]
    fn tolerates_spacing_and_skips_unfit_matches() {
        let html =
            r#"IG:"" junk IG:"OK1" data-iid="a.b" params_AbusePreventionHelper=[5 , "k" , 7]"#;
        let c = parse_page(html).unwrap();
        assert_eq!(c.ig, "OK1");
        assert_eq!(c.token, "k");
    }

    #[test]
    fn rejects_a_changed_page_layout() {
        for bad in [
            "<html>nothing useful here</html>",
            r#"IG:"A" data-iid="b" params_AbusePreventionHelper = [1,"t"]"#,
            r#"IG:"A" data-iid="b" params_AbusePreventionHelper = [x,"t",3]"#,
        ] {
            assert!(parse_page(bad).unwrap_err().contains("IG/IID"), "{bad}");
        }
    }

    #[test]
    fn reads_results_and_error_objects() {
        let ok = json!([{"translations": [{"text": "こんにちは", "to": "ja"}]}]);
        assert_eq!(
            parse_translation(&ok).unwrap(),
            Parsed::Text("こんにちは".into())
        );

        let empty_msg = json!({"statusCode": 400, "errorMessage": ""});
        let Parsed::ApiError(m) = parse_translation(&empty_msg).unwrap() else {
            panic!()
        };
        assert!(m.contains("statusCode=400"));
        let with_msg = json!({"statusCode": 429, "errorMessage": "slow down"});
        let Parsed::ApiError(m) = parse_translation(&with_msg).unwrap() else {
            panic!()
        };
        assert!(m.contains("slow down"));

        assert!(parse_translation(&json!([])).is_err());
    }

    #[test]
    fn cache_reuses_refreshes_and_counts() {
        let cache = CredCache::default();
        let fetches = AtomicUsize::new(0);
        let fetch = |exp| {
            fetches.fetch_add(1, Ordering::SeqCst);
            Ok(creds(exp))
        };
        let (_, n1, _) = cache.acquire(None, || 0.0, || fetch(100.0)).unwrap();
        let (_, n2, _) = cache.acquire(None, || 50.0, || fetch(100.0)).unwrap();
        assert_eq!((n1, n2, fetches.load(Ordering::SeqCst)), (1, 2, 1));
        // expired -> refetch; forced -> refetch
        let (_, _, generation) = cache.acquire(None, || 100.0, || fetch(1e9)).unwrap();
        cache
            .acquire(Some(generation), || 100.0, || fetch(1e9))
            .unwrap();
        assert_eq!(fetches.load(Ordering::SeqCst), 3);
    }

    #[test]
    fn a_failed_fetch_keeps_the_old_credentials_and_counter() {
        let cache = CredCache::default();
        let (_, _, generation) = cache.acquire(None, || 0.0, || Ok(creds(10.0))).unwrap();
        assert!(cache
            .acquire(Some(generation), || 0.0, || Err("boom".into()))
            .is_err());
        let (c, n, unchanged) = cache
            .acquire(None, || 0.0, || panic!("must not refetch"))
            .unwrap();
        assert_eq!((c.ig.as_str(), n), ("IG", 2));
        assert_eq!(unchanged, generation);
        let (_, seq, refreshed) = cache
            .acquire(Some(generation), || 0.0, || Ok(creds(20.0)))
            .unwrap();
        assert_eq!((seq, refreshed), (3, generation + 1));
    }

    #[test]
    fn fetches_once_under_concurrency() {
        let cache = CredCache::default();
        let fetches = AtomicUsize::new(0);
        std::thread::scope(|s| {
            for _ in 0..8 {
                s.spawn(|| {
                    cache
                        .acquire(
                            None,
                            || 0.0,
                            || {
                                fetches.fetch_add(1, Ordering::SeqCst);
                                std::thread::sleep(Duration::from_millis(30));
                                Ok(creds(1e9))
                            },
                        )
                        .unwrap();
                });
            }
        });
        assert_eq!(fetches.load(Ordering::SeqCst), 1);
        let (_, n, _) = cache.acquire(None, || 0.0, || panic!()).unwrap();
        assert_eq!(n, 9);
    }

    #[test]
    fn concurrent_rejections_share_one_successful_refresh() {
        let cache = CredCache::default();
        let (_, _, old) = cache.acquire(None, || 0.0, || Ok(creds(100.0))).unwrap();
        let refreshes = AtomicUsize::new(0);
        let ready = std::sync::Barrier::new(8);
        std::thread::scope(|scope| {
            for _ in 0..8 {
                scope.spawn(|| {
                    ready.wait();
                    let (_, _, generation) = cache
                        .acquire(
                            Some(old),
                            || 1.0,
                            || {
                                refreshes.fetch_add(1, Ordering::SeqCst);
                                Ok(creds(200.0))
                            },
                        )
                        .unwrap();
                    assert_eq!(generation, old + 1);
                });
            }
        });
        assert_eq!(refreshes.load(Ordering::SeqCst), 1);
        // Even an old rejection must refresh credentials that have now expired.
        let (_, sequence, generation) = cache
            .acquire(Some(old), || 200.0, || Ok(creds(300.0)))
            .unwrap();
        assert_eq!((sequence, generation), (10, old + 2));
    }

    #[test]
    fn retries_an_api_error_once_with_fresh_credentials() {
        for succeeds in [true, false] {
            let error = r#"{"statusCode":400,"errorMessage":""}"#;
            let final_body = if succeeds {
                r#"[{"translations":[{"text":"こんにちは"}]}]"#
            } else {
                error
            };
            let (result, requests) = scripted(
                vec![
                    response(200, &page(1, 3_600_000)),
                    response(200, error),
                    response(200, &page(2, 3_600_000)),
                    response(200, final_body),
                ],
                || {
                    Backend::translate(
                        &BingEngine::default(),
                        "Hello & こんにちは",
                        "auto-detect",
                        "ja",
                        Duration::from_secs(5),
                    )
                },
            );
            if succeeds {
                assert_eq!(result.unwrap(), "こんにちは");
            } else {
                assert!(result.unwrap_err().contains("statusCode=400"));
            }
            let methods: Vec<_> = requests.iter().map(|r| r.method().as_str()).collect();
            assert_eq!(methods, ["GET", "POST", "GET", "POST"]);
            for (index, r) in requests.iter().enumerate() {
                assert_eq!(r.timeout(), Some(&Duration::from_secs(5)));
                if index % 2 == 0 {
                    assert_eq!(r.url().as_str(), "https://www.bing.com/translator");
                } else {
                    assert_eq!(r.url().path(), "/ttranslatev3");
                    assert_eq!(r.headers()["Referer"], "https://www.bing.com/translator");
                    let query: std::collections::HashMap<_, _> =
                        r.url().query_pairs().into_owned().collect();
                    assert_eq!(query["IG"], "ABC123");
                    assert_eq!(query["IID"], format!("translator.5025.{}", index / 2 + 1));
                    let fields = form(r);
                    assert_eq!(fields["key"], (index / 2 + 1).to_string());
                    assert_eq!(fields["token"], "tok-1");
                    assert_eq!(fields["fromLang"], "auto-detect");
                    assert_eq!(fields["to"], "ja");
                    assert_eq!(fields["text"], "Hello & こんにちは");
                }
            }
        }
    }
}
