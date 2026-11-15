//! The log images against the Python version (native/testdata/overlay/images.json, written by
//! native/reference/export_overlay_image.py): the sizes, which the text widths and wrapping decide.
//! VRCT_OVERLAY_IMAGES=<dir> also writes the images as PPM-on-black for looking at them.
use serde_json::Value;
use std::path::{Path, PathBuf};
use vrct_overlay::image::{Image, OverlayImage, Token};

fn native() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..")
}

fn strings(v: &Value) -> Vec<String> {
    v.as_array().unwrap().iter().map(|s| s.as_str().unwrap().to_string()).collect()
}

fn tokens(v: &Value) -> Vec<Token> {
    v.as_array().unwrap().iter().map(|t| Token {
        orig: t["orig"].as_str().unwrap_or("").into(),
        hira: t["hira"].as_str().unwrap_or("").into(),
        hepburn: t["hepburn"].as_str().unwrap_or("").into(),
    }).collect()
}

fn save(image: &Image, name: &str) {
    let Some(dir) = std::env::var_os("VRCT_OVERLAY_IMAGES") else { return };
    let mut ppm = format!("P6 {} {} 255\n", image.width, image.height).into_bytes();
    for p in image.data.chunks_exact(4) {
        ppm.extend(p[..3].iter().map(|&c| (c as u32 * p[3] as u32 / 255) as u8));
    }
    std::fs::write(Path::new(&dir).join(format!("{name}.ppm")), ppm).unwrap();
}

#[test]
fn sizes_match_python() {
    let data: Value = serde_json::from_slice(&std::fs::read(native().join("testdata/overlay/images.json")).unwrap()).unwrap();
    let fonts = native().join("data/fonts");
    let mut problems = vec![];
    let mut overlay = OverlayImage::new(&fonts);
    for c in data["small"].as_array().unwrap() {
        let image = overlay.small_log(c["message"].as_str().unwrap(), c["language"].as_str().unwrap(), &strings(&c["translation"]),
            &strings(&c["target_language"]), &tokens(&c["transliteration_message"]),
            &c["transliteration_translation"].as_array().unwrap().iter().map(tokens).collect::<Vec<_>>()).unwrap();
        save(&image, &format!("small_{}", c["name"].as_str().unwrap()));
        let size = serde_json::json!([image.width, image.height]);
        if size != c["size"] {
            problems.push(format!("small {}: {size} != {}", c["name"], c["size"]));
        }
    }
    let mut overlay = OverlayImage::new(&fonts);
    for c in data["large"].as_array().unwrap() {
        let image = overlay.large_log(c["message_type"].as_str().unwrap(), c["message"].as_str(), c["language"].as_str().unwrap(),
            &strings(&c["translation"]), &strings(&c["target_language"]), &tokens(&c["transliteration_message"]),
            &c["transliteration_translation"].as_array().unwrap().iter().map(tokens).collect::<Vec<_>>()).unwrap();
        save(&image, &format!("large_{}", c["name"].as_str().unwrap()));
        let size = serde_json::json!([image.width, image.height]);
        if size != c["size"] {
            problems.push(format!("large {}: {size} != {}", c["name"], c["size"]));
        }
    }
    for p in &problems {
        eprintln!("{p}");
    }
    assert!(problems.is_empty(), "{} problems", problems.len());
}

/// master 76a5c5be (issue #121): a translation engine can return an empty string. It must not panic
/// (the Python large log divided by len(text)) and the next log image must still be made.
#[test]
fn empty_translations_still_make_an_image() {
    let fonts = native().join("data/fonts");
    let mut overlay = OverlayImage::new(&fonts);
    let empty = || vec![String::new()];
    let mixed = || vec!["Hello".to_string(), String::new()];
    let languages = |n: usize| vec!["English".to_string(); n];
    let none = |n: usize| vec![Vec::<Token>::new(); n];
    for translation in [empty(), mixed()] {
        let n = translation.len();
        let small = overlay.small_log("こんにちは", "Japanese", &translation, &languages(n), &[], &none(n)).unwrap();
        assert!(small.width > 0 && small.height > 0);
        let large = overlay.large_log("receive", Some("こんにちは"), "Japanese", &translation, &languages(n), &[], &none(n)).unwrap();
        assert!(large.width > 0 && large.height > 0);
    }
    // an empty message too, and the log keeps working afterwards
    let large = overlay.large_log("send", Some(""), "Japanese", &empty(), &languages(1), &[], &none(1)).unwrap();
    assert!(large.width > 0 && large.height > 0);
    let large = overlay.large_log("receive", Some("ok"), "English", &[], &[], &[], &[]).unwrap();
    assert!(large.width > 0 && large.height > 0);
}
