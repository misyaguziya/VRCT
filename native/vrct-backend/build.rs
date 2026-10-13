/// package.json's "version" (update_version.py copies it to tauri.conf.json and config.py too)
fn app_version() -> String {
    let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../package.json");
    println!("cargo:rerun-if-changed={path}");
    let text = std::fs::read_to_string(path).expect("package.json");
    let after = text.split("\"version\"").nth(1).expect("no version in package.json");
    after.split('"').nth(1).expect("version").to_string()
}

fn main() {
    println!("cargo:rustc-env=VRCT_VERSION={}", app_version());
    // VRCT-sidecar loads ctranslate2.dll at its first use, after main() put `_internal` (where the
    // installed DLLs are) on the DLL search path
    println!("cargo:rustc-link-arg-bins=/DELAYLOAD:ctranslate2.dll");
    println!("cargo:rustc-link-arg-bins=delayimp.lib");
}
