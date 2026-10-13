//! Processes (models/process_check.py and psutil's name()): whether SteamVR / VRChat is running,
//! and the executable name of a process.
use windows_sys::Win32::Foundation::CloseHandle;
use windows_sys::Win32::System::Threading::{OpenProcess, QueryFullProcessImageNameW, PROCESS_QUERY_LIMITED_INFORMATION};

pub use vrct_openvr::{is_process_running, is_steamvr_running};

use serde_json::Value;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, SocketAddr, ToSocketAddrs};

/// Bytes waiting in a pipe; None when `file` is not a pipe or the pipe is closed
pub fn pipe_available(file: &std::fs::File) -> Option<u32> {
    use std::os::windows::io::AsRawHandle;
    use windows_sys::Win32::System::Pipes::PeekNamedPipe;
    let mut available = 0u32;
    let ok = unsafe {
        PeekNamedPipe(file.as_raw_handle(), std::ptr::null_mut(), 0, std::ptr::null_mut(), &mut available, std::ptr::null_mut())
    };
    (ok != 0).then_some(available)
}

/// isAvailableWebSocketServer: an IPv4 TCP socket with SO_REUSEADDR binds to host:port (on Windows
/// that also succeeds on a port another socket listens on without exclusive use, as in Python)
pub fn is_available_server(host: &str, port: i64) -> bool {
    let Ok(port) = u16::try_from(port) else { return false };
    let Some(addr) = (host, port).to_socket_addrs().ok().and_then(|mut a| a.find(SocketAddr::is_ipv4)) else {
        return false;
    };
    let Ok(socket) = socket2::Socket::new(socket2::Domain::IPV4, socket2::Type::STREAM, None) else { return false };
    socket.set_reuse_address(true).is_ok() && socket.bind(&addr.into()).is_ok()
}

/// ipaddress.ip_address(value): a dotted IPv4 (no leading zeros), an IPv6 (with a %scope), or an
/// integer (a bool is one); anything else is not an address
pub fn ip_address(value: &Value) -> Option<IpAddr> {
    match value {
        Value::Bool(b) => Some(IpAddr::V4(Ipv4Addr::from(*b as u32))),
        Value::Number(n) if n.is_u64() => {
            let n = n.as_u64()?;
            Some(u32::try_from(n).map_or(IpAddr::V6(Ipv6Addr::from(n as u128)), |v4| IpAddr::V4(Ipv4Addr::from(v4))))
        }
        Value::String(s) => {
            if let Ok(v4) = s.parse::<Ipv4Addr>() {
                return Some(IpAddr::V4(v4));
            }
            let (addr, scope) = s.split_once('%').map_or((s.as_str(), None), |(a, z)| (a, Some(z)));
            if scope.is_some_and(|z| z.is_empty() || z.contains('%')) {
                return None;
            }
            addr.parse::<Ipv6Addr>().ok().map(IpAddr::V6)
        }
        _ => None,
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

/// The ids of this process's threads now
pub fn thread_ids() -> std::collections::HashSet<u32> {
    use windows_sys::Win32::System::Diagnostics::ToolHelp::{CreateToolhelp32Snapshot, Thread32First, Thread32Next, THREADENTRY32,
                                                           TH32CS_SNAPTHREAD};
    use windows_sys::Win32::System::Threading::GetCurrentProcessId;
    let mut ids = std::collections::HashSet::new();
    unsafe {
        let me = GetCurrentProcessId();
        let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
        if snapshot.is_null() || snapshot as isize == -1 {
            return ids;
        }
        let mut entry: THREADENTRY32 = std::mem::zeroed();
        entry.dwSize = std::mem::size_of::<THREADENTRY32>() as u32;
        let mut ok = Thread32First(snapshot, &mut entry);
        while ok != 0 {
            if entry.th32OwnerProcessID == me {
                ids.insert(entry.th32ThreadID);
            }
            ok = Thread32Next(snapshot, &mut entry);
        }
        CloseHandle(snapshot);
    }
    ids
}

/// background_priority: a thread below normal priority (heavy work after VR UI and VRChat)
pub fn lower_thread(id: u32) -> bool {
    use windows_sys::Win32::System::Threading::{OpenThread, SetThreadPriority, THREAD_PRIORITY_BELOW_NORMAL, THREAD_SET_INFORMATION};
    unsafe {
        let handle = OpenThread(THREAD_SET_INFORMATION, 0, id);
        if handle.is_null() {
            return false;
        }
        let ok = SetThreadPriority(handle, THREAD_PRIORITY_BELOW_NORMAL) != 0;
        CloseHandle(handle);
        ok
    }
}

/// lowerCurrentThread
pub fn lower_current_thread() {
    use windows_sys::Win32::System::Threading::{GetCurrentThread, SetThreadPriority, THREAD_PRIORITY_BELOW_NORMAL};
    unsafe {
        SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_BELOW_NORMAL);
    }
}

/// _quitApp: the process that started this one (the UI) is ended
pub fn terminate_parent() {
    use windows_sys::Win32::System::Diagnostics::ToolHelp::{CreateToolhelp32Snapshot, Process32FirstW, Process32NextW,
                                                           PROCESSENTRY32W, TH32CS_SNAPPROCESS};
    use windows_sys::Win32::System::Threading::{GetCurrentProcessId, TerminateProcess, PROCESS_TERMINATE};
    unsafe {
        let me = GetCurrentProcessId();
        let snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
        if snapshot.is_null() || snapshot as isize == -1 {
            return;
        }
        let mut entry: PROCESSENTRY32W = std::mem::zeroed();
        entry.dwSize = std::mem::size_of::<PROCESSENTRY32W>() as u32;
        let mut parent = None;
        let mut ok = Process32FirstW(snapshot, &mut entry);
        while ok != 0 {
            if entry.th32ProcessID == me {
                parent = Some(entry.th32ParentProcessID);
                break;
            }
            ok = Process32NextW(snapshot, &mut entry);
        }
        CloseHandle(snapshot);
        if let Some(pid) = parent {
            let process = OpenProcess(PROCESS_TERMINATE, 0, pid);
            if !process.is_null() {
                TerminateProcess(process, 1);
                CloseHandle(process);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn ip_addresses_as_python() {
        for ok in [json!("127.0.0.1"), json!("::1"), json!("fe80::1%eth0"), json!(2130706433), json!(true), json!("::ffff:1.2.3.4")] {
            assert!(ip_address(&ok).is_some(), "{ok}");
        }
        for bad in [json!("not-an-ip"), json!("01.2.3.4"), json!("1.2.3"), json!("::1%"), json!(1.5), json!(-1), json!(null), json!("")] {
            assert!(ip_address(&bad).is_none(), "{bad}");
        }
        assert!(ip_address(&json!("0.0.0.0")).unwrap().is_unspecified());
    }

    #[test]
    fn finds_this_process() {
        let me = process_name(std::process::id()).unwrap();
        assert!(me.to_lowercase().ends_with(".exe"));
        assert!(is_process_running(&me.to_uppercase()));
        assert!(!is_process_running("no-such-process-0a9f3c.exe"));
    }
}
