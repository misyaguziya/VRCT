//! Clipper 6.4.2 (the copy in pyclipper 1.4.0) for RapidOCR's unclip.
fn main() {
    println!("cargo:rerun-if-changed=third_party/clipper");
    cc::Build::new()
        .cpp(true)
        .file("third_party/clipper/clipper.cpp")
        .file("third_party/clipper/offset.cpp")
        .flag_if_supported("/EHsc")
        .warnings(false)
        .compile("vrct_clipper");
}
