//! The compute devices (utils.py: getComputeDeviceList, getBestComputeType): the CPU and, when this
//! build can run CTranslate2 on CUDA (cuBLAS can be loaded), each GPU with the compute types it
//! may use. GPU names come from the NVIDIA driver (nvcuda.dll).
use serde_json::{json, Value};
use std::sync::OnceLock;
use windows_sys::Win32::System::LibraryLoader::{GetProcAddress, LoadLibraryW};

const CUBLAS: &str = "cublas64_12.dll";

fn load(name: &str) -> Option<windows_sys::Win32::Foundation::HMODULE> {
    let wide: Vec<u16> = name.encode_utf16().chain([0]).collect();
    let module = unsafe { LoadLibraryW(wide.as_ptr()) };
    (!module.is_null()).then_some(module)
}

/// _getCudaDeviceNames: the CUDA devices CTranslate2 can use (names, "" when unknown); none
/// without cuBLAS (the CPU build) or a driver
pub fn cuda_device_names() -> &'static [String] {
    static NAMES: OnceLock<Vec<String>> = OnceLock::new();
    NAMES.get_or_init(|| {
        let count = vrct_ct2::cuda_device_count();
        if count == 0 || load(CUBLAS).is_none() {
            return vec![];
        }
        let mut names = vec![String::new(); count];
        let Some(cuda) = load("nvcuda.dll") else { return names };
        unsafe {
            let get = |name: &[u8]| GetProcAddress(cuda, name.as_ptr());
            let (Some(init), Some(device_get), Some(device_get_name)) =
                (get(b"cuInit\0"), get(b"cuDeviceGet\0"), get(b"cuDeviceGetName\0")) else { return names };
            let init: unsafe extern "system" fn(u32) -> i32 = std::mem::transmute(init);
            let device_get: unsafe extern "system" fn(*mut i32, i32) -> i32 = std::mem::transmute(device_get);
            let device_get_name: unsafe extern "system" fn(*mut u8, i32, i32) -> i32 = std::mem::transmute(device_get_name);
            if init(0) != 0 {
                return names;
            }
            for (index, slot) in names.iter_mut().enumerate() {
                let mut device = 0;
                if device_get(&mut device, index as i32) != 0 {
                    continue;
                }
                let mut buffer = [0u8; 256];
                if device_get_name(buffer.as_mut_ptr(), buffer.len() as i32, device) != 0 {
                    continue;
                }
                let end = buffer.iter().position(|&b| b == 0).unwrap_or(buffer.len());
                *slot = String::from_utf8_lossy(&buffer[..end]).into_owned();
            }
        }
        names
    })
}

fn sorted_types(device: &str, index: i32) -> Vec<String> {
    let mut types: Vec<String> = vrct_ct2::supported_compute_types(device, index).unwrap_or_default().into_iter().map(String::from).collect();
    types.sort();
    types
}

/// getComputeDeviceList: the CPU first, then each GPU (GTX without int8 / 16-bit types; other
/// than RTX / Tesla / A100 / Quadro float32 only)
pub fn device_list() -> Vec<Value> {
    let mut cpu_types = vec!["auto".to_string()];
    cpu_types.extend(sorted_types("cpu", 0));
    let mut devices = vec![json!({"device": "cpu", "device_index": 0, "device_name": "cpu", "compute_types": cpu_types})];
    for (index, name) in cuda_device_names().iter().enumerate() {
        let mut types = vec!["auto".to_string()];
        types.extend(sorted_types("cuda", index as i32));
        if name.contains("GTX") {
            types.retain(|t| !["int8_bfloat16", "bfloat16", "float16", "int8"].contains(&t.as_str()));
        } else if !["RTX", "Tesla", "A100", "Quadro"].iter().any(|k| name.contains(k)) {
            types = vec!["float32".into()];
        }
        devices.push(json!({"device": "cuda", "device_index": index, "device_name": name, "compute_types": types}));
    }
    devices
}

/// getBestComputeType: the device's preferred types (by its name) in order, the first supported
pub fn best_compute_type(device: &str, index: usize) -> String {
    let supported = vrct_ct2::supported_compute_types(device, index as i32).unwrap_or_default();
    let name = if device == "cpu" { "cpu".to_string() } else { cuda_device_names().get(index).cloned().unwrap_or_default() };
    const FULL: [&str; 7] = ["int8_bfloat16", "int8_float16", "int8", "bfloat16", "float16", "int8_float32", "float32"];
    // the first key the name contains, in the table's order ("default" first, which no name holds)
    let preferred: &[&str] = if name.contains("GTX") { &["float32"] } else { &FULL };
    preferred.iter().find(|t| supported.contains(t)).map_or_else(|| "float32".into(), |t| t.to_string())
}
