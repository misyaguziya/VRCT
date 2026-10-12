//! openvr_api.dll (`cargo xtask fetch-native` puts it in native/third_party/openvr/) copied
//! next to the binaries (target/<profile>/, deps/ for the tests, examples/).
use std::path::{Path, PathBuf};

fn main() {
    let dll = Path::new(env!("CARGO_MANIFEST_DIR")).join("../third_party/openvr/openvr_api.dll");
    println!("cargo:rerun-if-changed={}", dll.display());
    assert!(dll.exists(), "no {}: run `cargo xtask fetch-native` in native/", dll.display());
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    // OUT_DIR = target/<profile>/build/vrct-openvr-<hash>/out
    let profile_dir = out.ancestors().nth(3).unwrap();
    for dest_dir in [profile_dir.to_path_buf(), profile_dir.join("deps"), profile_dir.join("examples")] {
        let dest = dest_dir.join(dll.file_name().unwrap());
        let stale = std::fs::metadata(&dest).map(|d| d.len() != dll.metadata().unwrap().len()).unwrap_or(true);
        if stale {
            std::fs::copy(&dll, dest).unwrap();
        }
    }
}
