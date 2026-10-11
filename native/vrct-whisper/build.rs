//! Copies numpy's OpenBLAS (`cargo xtask fetch-native` puts it in native/third_party/numpy/) next to
//! the binaries (target/<profile>/ and deps/ for the tests); mel.rs loads it from the exe's folder.
use std::path::{Path, PathBuf};

fn main() {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../third_party/numpy");
    println!("cargo:rerun-if-changed={}", dir.display());
    let dll = std::fs::read_dir(&dir)
        .ok()
        .and_then(|d| d.flatten().map(|e| e.path()).find(|p| p.extension().is_some_and(|e| e == "dll")))
        .unwrap_or_else(|| panic!("no OpenBLAS DLL in {}: run `cargo xtask fetch-native` in native/", dir.display()));
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    // OUT_DIR = target/<profile>/build/vrct-whisper-<hash>/out
    let profile_dir = out.ancestors().nth(3).unwrap();
    for dest in [profile_dir.to_path_buf(), profile_dir.join("deps")] {
        let dest = dest.join(dll.file_name().unwrap());
        if !dest.is_file() {
            std::fs::copy(&dll, dest).unwrap();
        }
    }
}
