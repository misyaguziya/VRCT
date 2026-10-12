//! Processes (models/process_check.py and psutil's name()): whether SteamVR / VRChat is running,
//! and the executable name of a process.
use windows_sys::Win32::Foundation::{CloseHandle, INVALID_HANDLE_VALUE};
use windows_sys::Win32::System::Diagnostics::ToolHelp::{
    CreateToolhelp32Snapshot, Process32FirstW, Process32NextW, PROCESSENTRY32W, TH32CS_SNAPPROCESS,
};
use windows_sys::Win32::System::Threading::{OpenProcess, QueryFullProcessImageNameW, PROCESS_QUERY_LIMITED_INFORMATION};

/// A process named `name` (e.g. "vrmonitor.exe", case-insensitive) is running. A Toolhelp
/// snapshot: psutil's process list took ~2 s on a PC with 460 processes, this ~15 ms.
pub fn is_process_running(name: &str) -> bool {
    let wanted = name.to_lowercase();
    unsafe {
        let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if snapshot == INVALID_HANDLE_VALUE || snapshot.is_null() {
            return false;
        }
        let mut entry: PROCESSENTRY32W = std::mem::zeroed();
        entry.dwSize = size_of::<PROCESSENTRY32W>() as u32;
        let mut found = Process32FirstW(snapshot, &mut entry) != 0;
        let mut running = false;
        while found {
            let len = entry.szExeFile.iter().position(|&c| c == 0).unwrap_or(entry.szExeFile.len());
            if String::from_utf16_lossy(&entry.szExeFile[..len]).to_lowercase() == wanted {
                running = true;
                break;
            }
            found = Process32NextW(snapshot, &mut entry) != 0;
        }
        CloseHandle(snapshot);
        running
    }
}

/// The executable's file name of a process (psutil.Process(pid).name())
pub fn process_name(pid: u32) -> Option<String> {
    unsafe {
        let process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid);
        if process.is_null() {
            return None;
        }
        let mut buf = [0u16; 1024];
        let mut len = buf.len() as u32;
        let ok = QueryFullProcessImageNameW(process, 0, buf.as_mut_ptr(), &mut len);
        CloseHandle(process);
        if ok == 0 {
            return None;
        }
        let path = String::from_utf16_lossy(&buf[..len as usize]);
        path.rsplit(['\\', '/']).next().map(String::from)
    }
}

/// SteamVR is running (checkSteamvrRunning / _isSteamvrRunning)
pub fn is_steamvr_running() -> bool {
    is_process_running("vrmonitor.exe")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_this_process() {
        let me = process_name(std::process::id()).unwrap();
        assert!(me.to_lowercase().ends_with(".exe"));
        assert!(is_process_running(&me.to_uppercase()));
        assert!(!is_process_running("no-such-process-0a9f3c.exe"));
    }
}
