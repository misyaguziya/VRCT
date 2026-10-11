//! Links against the ctranslate2.dll of the Python wheel (`cargo xtask fetch-native` puts it and the
//! headers of the same version in native/third_party/ctranslate2/).
//!
//! CT2_DLL_DIR / CT2_INCLUDE_DIR override those folders.
//!
//! The wheel has no import library, so one is made from the DLL's export table (lib.exe /def). The
//! DLLs are copied next to the binaries (target/<profile>/ and deps/ for the tests) so they run
//! without PATH changes.
use std::env;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};

fn main() {
    println!("cargo:rerun-if-changed=shim/ct2_shim.cpp");
    println!("cargo:rerun-if-env-changed=CT2_DLL_DIR");
    println!("cargo:rerun-if-env-changed=CT2_INCLUDE_DIR");
    let third_party = Path::new(env!("CARGO_MANIFEST_DIR")).join("../third_party/ctranslate2");
    let dll_dir = env::var_os("CT2_DLL_DIR").map(PathBuf::from).unwrap_or_else(|| third_party.clone());
    let include_dir = env::var_os("CT2_INCLUDE_DIR").map(PathBuf::from).unwrap_or_else(|| third_party.join("include"));
    let dll_path = dll_dir.join("ctranslate2.dll");
    assert!(dll_path.is_file(), "{} not found: run `cargo xtask fetch-native` in native/", dll_path.display());
    println!("cargo:rerun-if-changed={}", dll_path.display());
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let target = env::var("TARGET").unwrap();

    // ctranslate2.def from the export table, then ctranslate2.lib
    let dll = std::fs::read(&dll_path).expect("ctranslate2.dll");
    let pe = object::read::pe::PeFile64::parse(&*dll).expect("PE");
    let mut def = String::from("LIBRARY ctranslate2.dll\nEXPORTS\n");
    for export in pe.export_table().expect("exports").expect("no export table").exports().expect("exports") {
        if let Some(name) = export.name {
            writeln!(def, "    {}", String::from_utf8_lossy(name)).unwrap();
        }
    }
    std::fs::write(out.join("ctranslate2.def"), def).unwrap();
    let status = cc::windows_registry::find_tool(&target, "lib.exe")
        .expect("lib.exe")
        .to_command()
        .arg(format!("/def:{}", out.join("ctranslate2.def").display()))
        .arg("/machine:x64")
        .arg(format!("/out:{}", out.join("ctranslate2.lib").display()))
        .arg("/nologo")
        .status()
        .unwrap();
    assert!(status.success(), "lib.exe failed");

    // /MD (cc's default without +crt-static), C++17 as CTranslate2 requires
    cc::Build::new()
        .cpp(true)
        .file("shim/ct2_shim.cpp")
        .include(&include_dir)
        .flag("/std:c++17")
        .flag("/EHsc")
        .define("NDEBUG", None)
        .compile("ct2_shim");
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=dylib=ctranslate2");

    // OUT_DIR = target/<profile>/build/vrct-ct2-<hash>/out
    let profile_dir = out.ancestors().nth(3).unwrap();
    for dir in [profile_dir.to_path_buf(), profile_dir.join("deps")] {
        for entry in std::fs::read_dir(&dll_dir).unwrap().flatten() {
            let path = entry.path();
            if path.extension().is_some_and(|e| e.eq_ignore_ascii_case("dll")) {
                let dest = dir.join(entry.file_name());
                let stale = std::fs::metadata(&dest).map(|d| d.len() != entry.metadata().unwrap().len()).unwrap_or(true);
                if stale {
                    std::fs::copy(&path, &dest).unwrap();
                }
            }
        }
    }
}
