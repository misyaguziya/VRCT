fn main() {
    // The exe's FileVersion / ProductVersion strings: tauri-winres takes them from CARGO_PKG_VERSION
    // (this crate's 0.0.0). The app's version is package.json's, as tauri.conf.json's.
    println!("cargo:rerun-if-changed=../package.json");
    let package: serde_json::Value =
        serde_json::from_slice(&std::fs::read("../package.json").expect("package.json")).expect("package.json");
    let version = package["version"].as_str().expect("package.json version");
    std::env::set_var("CARGO_PKG_VERSION", version);
    tauri_build::build()
}
