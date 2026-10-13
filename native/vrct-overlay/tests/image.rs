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
