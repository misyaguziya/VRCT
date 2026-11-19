//! Check-only DLL: never link CT2 into the Rust supervisor or copy the app's DLL.
use std::env;
use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::process::Command;

fn checked(command: &mut Command, what: &str) {
    assert!(
        command
            .status()
            .unwrap_or_else(|e| panic!("{what}: {e}"))
            .success(),
        "{what} failed"
    );
}

fn main() {
    build_ct2();
    build_whisper();
}

fn build_ct2() {
    println!("cargo:rustc-check-cfg=cfg(ct2_49_adapter)");
    println!("cargo:rerun-if-env-changed=VRCT_CT2_49_INCLUDE");
    println!("cargo:rerun-if-env-changed=VRCT_CT2_49_DLL_DIR");
    println!("cargo:rerun-if-changed=adapter/ct2_49.cpp");
    let Some(include) = env::var_os("VRCT_CT2_49_INCLUDE").map(PathBuf::from) else {
        return;
    };
    assert!(
        include.join("ctranslate2/models/whisper.h").is_file(),
        "VRCT_CT2_49_INCLUDE must contain the official v4.9.0 ctranslate2 headers"
    );
    // Require the official source checkout layout, not an arbitrary installed
    // include directory accidentally pointing at the app's 4.6 headers.
    // 4.9.0 のソースは版を CMakeLists.txt ではなく python/ctranslate2/version.py に持つ
    // (CMakeLists.txt がそれを読む)
    let version_py = include
        .parent()
        .expect("source root")
        .join("python/ctranslate2/version.py");
    println!("cargo:rerun-if-changed={}", version_py.display());
    let source = std::fs::read_to_string(&version_py)
        .expect("VRCT_CT2_49_INCLUDE must be include/ inside the official v4.9.0 source tree");
    let version = regex::Regex::new(r#"(?m)^__version__\s*=\s*"4\.9\.0"\s*$"#).unwrap();
    assert!(
        version.is_match(&source),
        "expected __version__ = \"4.9.0\" in {}",
        version_py.display()
    );
    let dll_dir = env::var_os("VRCT_CT2_49_DLL_DIR")
        .map(PathBuf::from)
        .expect("VRCT_CT2_49_DLL_DIR is required with VRCT_CT2_49_INCLUDE (matching 4.9.0 DLL)");
    let dll = dll_dir.join("ctranslate2.dll");
    println!("cargo:rerun-if-changed={}", include.display());
    println!("cargo:rerun-if-changed={}", dll.display());
    let bytes = std::fs::read(&dll).expect("read the supplied 4.9.0 ctranslate2.dll");
    let pe = object::read::pe::PeFile64::parse(&*bytes).expect("Windows x64 CT2 PE image");
    let mut def = String::from("LIBRARY ctranslate2.dll\nEXPORTS\n");
    for export in pe
        .export_table()
        .expect("exports")
        .expect("export table")
        .exports()
        .expect("export entries")
    {
        if let Some(name) = export.name {
            writeln!(
                def,
                "    {}",
                std::str::from_utf8(name).expect("export name")
            )
            .unwrap();
        }
    }
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    std::fs::write(out.join("ctranslate2.def"), def).unwrap();
    let target = env::var("TARGET").unwrap();
    assert_eq!(
        target, "x86_64-pc-windows-msvc",
        "adapter needs Windows x64 MSVC"
    );
    let import = out.join("ctranslate2.lib");
    checked(
        cc::windows_registry::find_tool(&target, "lib.exe")
            .expect("MSVC lib.exe")
            .to_command()
            .arg("/nologo")
            .arg("/machine:x64")
            .arg(format!("/def:{}", out.join("ctranslate2.def").display()))
            .arg(format!("/out:{}", import.display())),
        "CT2 import library",
    );

    // The adapter must use the release DLL CRT/STL even if Rust uses +crt-static or Debug.
    let object = out.join("ct2_49.obj");
    let compiler = cc::Build::new()
        .cpp(true)
        .static_crt(false)
        .opt_level(2)
        .debug(false)
        .cargo_metadata(false)
        .get_compiler();
    checked(
        compiler
            .to_command()
            .args([
                "/nologo",
                "/c",
                "/std:c++17",
                "/EHsc",
                "/MD",
                "/O2",
                "/DNDEBUG",
                "/D_ITERATOR_DEBUG_LEVEL=0",
                "/utf-8",
            ])
            .arg(format!("/I{}", include.display()))
            .arg(Path::new(env!("CARGO_MANIFEST_DIR")).join("adapter/ct2_49.cpp"))
            .arg(format!("/Fo{}", object.display())),
        "4.9.0 adapter compilation",
    );
    let adapter = out.join("vrct_ct2_49_adapter.dll");
    checked(
        cc::windows_registry::find_tool(&target, "link.exe")
            .expect("MSVC link.exe")
            .to_command()
            .args(["/NOLOGO", "/DLL", "/MACHINE:X64"])
            .arg(&object)
            .arg(&import)
            .arg("kernel32.lib")
            .arg(format!("/OUT:{}", adapter.display()))
            .arg(format!(
                "/IMPLIB:{}",
                out.join("vrct_ct2_49_adapter.lib").display()
            )),
        "4.9.0 adapter link",
    );
    // No CT2/dependency DLL is copied here: packaging is explicit and isolated from the app.
    let profile = out.ancestors().nth(3).expect("Cargo profile directory");
    for dir in [profile.to_path_buf(), profile.join("deps")] {
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::copy(&adapter, dir.join("vrct_ct2_49_adapter.dll")).unwrap();
    }
    println!("cargo:rustc-cfg=ct2_49_adapter");
}

fn build_whisper() {
    use sha2::{Digest, Sha256};
    println!("cargo:rustc-check-cfg=cfg(whisper_184_adapter)");
    println!("cargo:rerun-if-env-changed=VRCT_WHISPER_184_ROOT");
    println!("cargo:rerun-if-env-changed=VRCT_WHISPER_184_DLL_DIR");
    println!("cargo:rerun-if-changed=adapter/whisper_184.cpp");
    println!("cargo:rerun-if-changed=adapter/token_budget.h");
    println!("cargo:rerun-if-changed=adapter/token_budget_test.cpp");
    println!("cargo:rerun-if-changed=adapter/mel_input.h");
    println!("cargo:rerun-if-changed=adapter/mel_input_test.cpp");
    let Some(root) = env::var_os("VRCT_WHISPER_184_ROOT").map(PathBuf::from) else {
        return;
    };
    // 構造体 ABI を手書きしない。使用するヘッダーも同じ fork/tag に固定する。
    for (file, sha) in [
        (
            "include/whisper.h",
            "6c1c70a5d4b74556f4253e51a13874ad013513b0ae62e779c0e30ffde3dc30ba",
        ),
        (
            "ggml/include/ggml.h",
            "6fcc3c4efd5c3747b66281a800f1dd9b7d0d61182faa9bc731925bfdf0586b22",
        ),
        (
            "ggml/include/ggml-cpu.h",
            "1aafe97e576ea38c0da57517fb2492955d0b69c1a799842481fc069d6d9d28ef",
        ),
        (
            "ggml/include/ggml-backend.h",
            "f7f511270a8260859146e87544f64ef97f80e98bff179ae3ab02ca27cf7299c7",
        ),
        (
            "ggml/include/ggml-alloc.h",
            "3793a2175be355619cc426982706b7fa94ad801b66d2aeef4b95e68c434ba0ef",
        ),
    ] {
        let path = root.join(file);
        println!("cargo:rerun-if-changed={}", path.display());
        let bytes = std::fs::read(&path).expect("read pinned whisper.cpp v1.8.4 header");
        assert_eq!(
            format!("{:x}", Sha256::digest(bytes)),
            sha,
            "wrong header: {}",
            path.display()
        );
    }
    let dll_dir = env::var_os("VRCT_WHISPER_184_DLL_DIR")
        .map(PathBuf::from)
        .expect("VRCT_WHISPER_184_DLL_DIR is required with VRCT_WHISPER_184_ROOT");
    let dll = dll_dir.join("whisper.dll");
    println!("cargo:rerun-if-changed={}", dll.display());
    let bytes = std::fs::read(&dll).expect("read matching whisper.dll");
    let pe = object::read::pe::PeFile64::parse(&*bytes).expect("Windows x64 whisper PE image");
    let mut def = String::from("LIBRARY whisper.dll\nEXPORTS\n");
    for export in pe
        .export_table()
        .expect("exports")
        .expect("export table")
        .exports()
        .expect("export entries")
    {
        if let Some(name) = export.name {
            writeln!(
                def,
                "    {}",
                std::str::from_utf8(name).expect("export name")
            )
            .unwrap();
        }
    }
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
    std::fs::write(out.join("whisper.def"), def).unwrap();
    let target = env::var("TARGET").unwrap();
    assert_eq!(
        target, "x86_64-pc-windows-msvc",
        "adapter needs Windows x64 MSVC"
    );
    let import = out.join("whisper.lib");
    checked(
        cc::windows_registry::find_tool(&target, "lib.exe")
            .expect("MSVC lib.exe")
            .to_command()
            .args(["/nologo", "/machine:x64"])
            .arg(format!("/def:{}", out.join("whisper.def").display()))
            .arg(format!("/out:{}", import.display())),
        "whisper import library",
    );
    let object = out.join("whisper_184.obj");
    let compiler = cc::Build::new()
        .cpp(true)
        .static_crt(false)
        .opt_level(2)
        .debug(false)
        .cargo_metadata(false)
        .get_compiler();
    for test in ["token_budget_test", "mel_input_test"] {
        let executable = out.join(format!("{test}.exe"));
        checked(
            compiler
                .to_command()
                .args(["/nologo", "/std:c++17", "/EHsc", "/MD", "/O2", "/utf-8"])
                .arg(Path::new(env!("CARGO_MANIFEST_DIR")).join(format!("adapter/{test}.cpp")))
                .arg(format!("/Fo{}", out.join(format!("{test}.obj")).display()))
                .arg(format!("/Fe{}", executable.display())),
            "native input boundary test compilation",
        );
        checked(&mut Command::new(&executable), "native input boundary test");
    }
    checked(
        compiler
            .to_command()
            .args([
                "/nologo",
                "/c",
                "/std:c++17",
                "/EHsc",
                "/MD",
                "/O2",
                "/DNDEBUG",
                "/D_ITERATOR_DEBUG_LEVEL=0",
                "/DWHISPER_SHARED",
                "/utf-8",
            ])
            .arg(format!("/I{}", root.join("include").display()))
            .arg(format!("/I{}", root.join("ggml/include").display()))
            .arg(Path::new(env!("CARGO_MANIFEST_DIR")).join("adapter/whisper_184.cpp"))
            .arg(format!("/Fo{}", object.display())),
        "whisper adapter compilation",
    );
    let adapter = out.join("vrct_whisper_184_adapter.dll");
    checked(
        cc::windows_registry::find_tool(&target, "link.exe")
            .expect("MSVC link.exe")
            .to_command()
            .args(["/NOLOGO", "/DLL", "/MACHINE:X64"])
            .arg(object)
            .arg(import)
            .arg("kernel32.lib")
            .arg(format!("/OUT:{}", adapter.display()))
            .arg(format!(
                "/IMPLIB:{}",
                out.join("vrct_whisper_184_adapter.lib").display()
            )),
        "whisper adapter link",
    );
    let profile = out.ancestors().nth(3).expect("Cargo profile directory");
    for dir in [profile.to_path_buf(), profile.join("deps")] {
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::copy(&adapter, dir.join("vrct_whisper_184_adapter.dll")).unwrap();
    }
    println!("cargo:rustc-cfg=whisper_184_adapter");
}
