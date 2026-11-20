//! CTranslate2 compute devices. Both CUDA and ROCm call their GPU device "cuda".
use serde_json::{json, Value};
use std::collections::HashSet;
use std::ffi::CStr;
use std::path::Path;
use windows_sys::Win32::System::LibraryLoader::{GetModuleHandleA, GetProcAddress, LoadLibraryW};

const CUBLAS: &str = "cublas64_12.dll";

fn load(name: &str) -> Option<windows_sys::Win32::Foundation::HMODULE> {
    let wide: Vec<u16> = name.encode_utf16().chain([0]).collect();
    let module = unsafe { LoadLibraryW(wide.as_ptr()) };
    (!module.is_null()).then_some(module)
}

// hipDeviceGetName and cuDeviceGetName share this signature. An unknown name keeps its CT2 index.
type DeviceGetName = unsafe extern "system" fn(*mut u8, i32, i32) -> i32;

fn device_name(get_name: DeviceGetName, device: i32) -> String {
    let mut buffer = [0u8; 256];
    if unsafe { get_name(buffer.as_mut_ptr(), buffer.len() as i32, device) } != 0 {
        return String::new();
    }
    let end = buffer.iter().position(|&b| b == 0).unwrap_or(buffer.len());
    String::from_utf8_lossy(&buffer[..end]).into_owned()
}

fn nvidia_names(count: usize) -> Vec<String> {
    if count == 0 || load(CUBLAS).is_none() {
        return vec![];
    }
    let mut names = vec![String::new(); count];
    if let Some(cuda) = load("nvcuda.dll") {
        unsafe {
            let get = |name: &[u8]| GetProcAddress(cuda, name.as_ptr());
            let (Some(init), Some(device_get), Some(get_name)) =
                (get(b"cuInit\0"), get(b"cuDeviceGet\0"), get(b"cuDeviceGetName\0")) else { return names };
            let init: unsafe extern "system" fn(u32) -> i32 = std::mem::transmute(init);
            let device_get: unsafe extern "system" fn(*mut i32, i32) -> i32 = std::mem::transmute(device_get);
            let get_name: DeviceGetName = std::mem::transmute(get_name);
            if init(0) == 0 {
                for (index, slot) in names.iter_mut().enumerate() {
                    let mut device = 0;
                    if device_get(&mut device, index as i32) == 0 {
                        *slot = device_name(get_name, device);
                    }
                }
            }
        }
    }
    names
}

fn arch_tokens(filename: &str) -> impl Iterator<Item = &str> {
    filename.split(|c: char| !c.is_ascii_alphanumeric()).filter(|s| s.starts_with("gfx"))
}

fn kernel_arches(dir: &Path) -> std::io::Result<HashSet<String>> {
    let mut arches = HashSet::new();
    let mut has_files = false;
    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        if entry.file_type()?.is_file() {
            has_files = true;
            arches.extend(arch_tokens(&entry.file_name().to_string_lossy()).map(str::to_owned));
        }
    }
    if !has_files {
        return Err(std::io::Error::other("empty kernel library"));
    }
    Ok(arches)
}

fn bundled_arches(resources: &Path) -> HashSet<String> {
    let rocm = resources.join("ct2-rocm");
    let scan = |dir: &str| {
        let path = rocm.join(dir);
        kernel_arches(&path).inspect_err(|e| crate::logs::PROCESS.write(&format!("Could not scan {}: {e}", path.display())))
    };
    let (Ok(mut arches), Ok(lt)) = (scan("rocblas/library"), scan("hipblaslt/library")) else { return HashSet::new() };
    if !lt.is_empty() {
        arches.retain(|arch| lt.contains(arch));
    }
    arches
}

// ROCm 7.2 hipDeviceProp_tR0600 layout, checked in vrct-amd-check/src/hip_abi.rs.
#[repr(C, align(8))]
struct HipProperties([u8; 1472]);
type GetProperties = unsafe extern "system" fn(*mut HipProperties, i32) -> i32;

impl HipProperties {
    fn arch(&self) -> Option<&str> {
        let name = CStr::from_bytes_until_nul(&self.0[1160..1160 + 256]).ok()?.to_str().ok()?;
        name.split(':').next().filter(|s| !s.is_empty())
    }
}

fn radeon_devices(count: usize, resources: &Path) -> Vec<(usize, String)> {
    let supported = bundled_arches(resources);
    // preload_rocm pinned this System32 module.
    let hip = unsafe { GetModuleHandleA(c"amdhip64_7.dll".as_ptr().cast()) };
    let get_name = unsafe { GetProcAddress(hip, c"hipDeviceGetName".as_ptr().cast()).map(|f| std::mem::transmute::<_, DeviceGetName>(f)) };
    let properties = unsafe {
        GetProcAddress(hip, c"hipGetDevicePropertiesR0600".as_ptr().cast()).map(|f| std::mem::transmute::<_, GetProperties>(f))
    };
    let mut devices = Vec::new();
    for index in 0..count {
        let mut name = get_name.map(|f| device_name(f, index as i32)).unwrap_or_default();
        if name.is_empty() {
            name = format!("Radeon device {index}");
        }
        let mut prop = HipProperties([0; 1472]);
        let ok = properties.is_some_and(|f| unsafe { f(&mut prop, index as i32) } == 0);
        let arch = if ok { prop.arch() } else { None }.unwrap_or("unknown");
        let used = supported.contains(arch);
        let status = if used { "used" } else { "no bundled kernels, not used" };
        crate::logs::PROCESS.write(&format!("{name} ({arch}): {status}"));
        if used {
            devices.push((index, name));
        }
    }
    if devices.is_empty() {
        crate::logs::PROCESS.write("Using CPU: ROCm loaded but no usable Radeon was found");
    }
    devices
}

/// The edition installed (its bundled DLLs), whatever this PC's GPU and driver: "amd" | "cuda" | "cpu"
pub fn installed_edition(resources: &Path) -> &'static str {
    if resources.join("ct2-rocm").join("ctranslate2.dll").is_file() {
        "amd"
    } else if resources.join(CUBLAS).is_file() {
        "cuda"
    } else {
        "cpu"
    }
}

fn sorted_types(device: &str, index: i32) -> Vec<String> {
    let mut types: Vec<String> = vrct_ct2::supported_compute_types(device, index).unwrap_or_default().into_iter().map(String::from).collect();
    types.sort();
    types
}

/// getComputeDeviceList: the CPU first, then each GPU (GTX without int8 / 16-bit types; other
/// than RTX / Tesla / A100 / Quadro float32 only)
pub fn device_list(rocm: bool, resources: &Path) -> Vec<Value> {
    let mut cpu_types = vec!["auto".to_string()];
    cpu_types.extend(sorted_types("cpu", 0));
    let mut devices = vec![json!({"device": "cpu", "device_index": 0, "device_name": "cpu", "compute_types": cpu_types})];
    let count = vrct_ct2::cuda_device_count();
    let gpus = if rocm { radeon_devices(count, resources) } else { nvidia_names(count).into_iter().enumerate().collect() };
    for (index, name) in gpus {
        let mut types = vec!["auto".to_string()];
        types.extend(sorted_types("cuda", index as i32));
        if !rocm && name.contains("GTX") {
            types.retain(|t| !["int8_bfloat16", "bfloat16", "float16", "int8"].contains(&t.as_str()));
        } else if !rocm && !["RTX", "Tesla", "A100", "Quadro"].iter().any(|k| name.contains(k)) {
            types = vec!["float32".into()];
        }
        let vendor = if rocm { "amd" } else { "nvidia" };
        devices.push(json!({"device": "cuda", "device_index": index, "device_name": name, "compute_types": types, "vendor": vendor}));
    }
    devices
}

/// Resolve "auto" for the selected device from the enumerated list.
pub fn best_compute_type(device: &Value) -> &'static str {
    if device["vendor"] == "amd" {
        let supported = device["compute_types"].as_array().map(Vec::as_slice).unwrap_or_default();
        return ["float16", "int8_float16", "int8_float32", "float32"].into_iter()
            .find(|t| supported.iter().any(|s| s == t)).unwrap_or("float32");
    }
    vrct_ct2::best_compute_type(device["device"].as_str().unwrap_or("cpu"),
                                device["device_index"].as_i64().unwrap_or(0) as i32,
                                device["device_name"].as_str().unwrap_or_default())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn installed_edition_from_the_bundled_dlls() {
        let dir = std::env::temp_dir().join(format!("vrct-edition-{}", std::process::id()));
        std::fs::create_dir_all(dir.join("ct2-rocm")).unwrap();
        assert_eq!(installed_edition(&dir), "cpu");
        std::fs::write(dir.join(CUBLAS), b"").unwrap();
        assert_eq!(installed_edition(&dir), "cuda");
        std::fs::write(dir.join("ct2-rocm").join("ctranslate2.dll"), b"").unwrap();
        assert_eq!(installed_edition(&dir), "amd");
        let _ = std::fs::remove_dir_all(dir);
    }

    #[test]
    fn matches_hip_arch_to_kernel_filenames() {
        let mut prop = HipProperties([0; 1472]);
        let arch = b"gfx1100:sramecc-:xnack-";
        prop.0[1160..1160 + arch.len()].copy_from_slice(arch);
        assert_eq!(prop.arch(), Some("gfx1100"));
        for (name, expected) in [
            ("Kernels.so-000-gfx1100.hsaco", Some("gfx1100")),
            ("TensileLibrary_lazy_gfx1151.dat", Some("gfx1151")),
            ("extop_gfx1201.co", Some("gfx1201")),
            ("hipblasltExtOpLibrary.dat", None),
        ] {
            assert!(arch_tokens(name).eq(expected));
        }
    }

    #[test]
    fn radeon_auto_uses_the_first_supported_type() {
        let types = ["float16", "int8_float16", "int8_float32", "float32"];
        for (i, expected) in types.iter().enumerate() {
            let supported: Vec<_> = ["int8_bfloat16", "bfloat16"].into_iter().chain(types[i..].iter().rev().copied()).collect();
            assert_eq!(best_compute_type(&json!({"vendor": "amd", "compute_types": supported})), *expected);
        }
    }
}
