//! Clipper 6.4.2 (the copy in pyclipper 1.4.0) for RapidOCR's unclip, and onnxruntime.dll
//! (`cargo xtask fetch-native` puts it in native/third_party/onnxruntime/) copied next to the
//! binaries (target/<profile>/ and deps/ for the tests).
use std::path::{Path, PathBuf};

fn main() {
    println!("cargo:rerun-if-changed=third_party/clipper");
    cc::Build::new()
        .cpp(true)
        .file("third_party/clipper/clipper.cpp")
        .file("third_party/clipper/offset.cpp")
        .flag_if_supported("/EHsc")
        .warnings(false)
        .compile("vrct_clipper");

    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../third_party/onnxruntime");
    println!("cargo:rerun-if-changed={}", dir.display());
    let dlls: Vec<PathBuf> = std::fs::read_dir(&dir)
        .map(|d| d.flatten().map(|e| e.path()).filter(|p| p.extension().is_some_and(|e| e == "dll")).collect())
        .unwrap_or_default();
    assert!(!dlls.is_empty(), "no onnxruntime.dll in {}: run `cargo xtask fetch-native` in native/", dir.display());
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    // OUT_DIR = target/<profile>/build/vrct-ocr-<hash>/out
    let profile_dir = out.ancestors().nth(3).unwrap();
    for dest_dir in [profile_dir.to_path_buf(), profile_dir.join("deps")] {
        for dll in &dlls {
            let dest = dest_dir.join(dll.file_name().unwrap());
            let stale = std::fs::metadata(&dest).map(|d| d.len() != dll.metadata().unwrap().len()).unwrap_or(true);
            if stale {
                std::fs::copy(dll, dest).unwrap();
            }
        }
    }
}
