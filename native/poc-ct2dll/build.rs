//! Links against the ctranslate2.dll of the Python wheel.
//!
//! CT2_DLL_DIR     folder with ctranslate2.dll (the wheel ships it with libiomp5md.dll and cudnn64_9.dll)
//! CT2_INCLUDE_DIR CTranslate2 headers of the same version (4.6.0: include/ of the v4.6.0 tag)
//!
//! The wheel has no import library, so one is made from the DLL's export table (lib.exe /def).
use std::env;
use std::fmt::Write as _;
use std::path::PathBuf;

fn main() {
    println!("cargo:rerun-if-changed=shim/ct2_shim.cpp");
    println!("cargo:rerun-if-env-changed=CT2_DLL_DIR");
    println!("cargo:rerun-if-env-changed=CT2_INCLUDE_DIR");
    let dll_dir = PathBuf::from(env::var("CT2_DLL_DIR").expect("CT2_DLL_DIR"));
    let include_dir = PathBuf::from(env::var("CT2_INCLUDE_DIR").expect("CT2_INCLUDE_DIR"));
    let out = PathBuf::from(env::var("OUT_DIR").unwrap());
    let target = env::var("TARGET").unwrap();

    // ctranslate2.def from the export table, then ctranslate2.lib
    let dll = std::fs::read(dll_dir.join("ctranslate2.dll")).expect("ctranslate2.dll");
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
}
