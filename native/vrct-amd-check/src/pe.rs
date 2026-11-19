use anyhow::{bail, ensure, Context, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct Imports {
    pub machine: u16,
    pub regular: Vec<String>,
    pub delay: Vec<String>,
}

impl Imports {
    pub fn family(&self) -> &'static str {
        let names: Vec<_> = self
            .regular
            .iter()
            .chain(&self.delay)
            .map(|n| n.to_ascii_lowercase())
            .collect();
        let hip = names.iter().any(|n| {
            ["amdhip", "hipblas", "rocblas", "hiprt"]
                .iter()
                .any(|k| n.contains(k))
        });
        let cuda = names.iter().any(|n| {
            ["cudart", "cublas", "nvcuda", "cudnn"]
                .iter()
                .any(|k| n.contains(k))
        });
        match (hip, cuda) {
            (true, false) => "rocm",
            (false, true) => "cuda",
            (true, true) => "mixed",
            _ => "unknown",
        }
    }
}

fn bytes(data: &[u8], at: usize, len: usize) -> Result<&[u8]> {
    data.get(at..at.checked_add(len).context("PE offset overflow")?)
        .context("truncated PE")
}
fn u16_at(data: &[u8], at: usize) -> Result<u16> {
    Ok(u16::from_le_bytes(bytes(data, at, 2)?.try_into()?))
}
fn u32_at(data: &[u8], at: usize) -> Result<u32> {
    Ok(u32::from_le_bytes(bytes(data, at, 4)?.try_into()?))
}

pub fn read(path: &Path) -> Result<Imports> {
    // 不明な巨大ファイルをメモリへ読み込まない。
    ensure!(
        std::fs::metadata(path)?.len() <= 512 * 1024 * 1024,
        "PE file exceeds 512 MiB"
    );
    parse(&std::fs::read(path)?)
}

pub fn parse(data: &[u8]) -> Result<Imports> {
    ensure!(bytes(data, 0, 2)? == b"MZ", "not an MZ image");
    let pe = u32_at(data, 0x3c)? as usize;
    ensure!(bytes(data, pe, 4)? == b"PE\0\0", "not a PE image");
    let machine = u16_at(data, pe + 4)?;
    let nsec = usize::from(u16_at(data, pe + 6)?);
    ensure!(nsec <= 96, "too many PE sections");
    let opt_len = usize::from(u16_at(data, pe + 20)?);
    let opt = pe + 24;
    let optional = bytes(data, opt, opt_len)?;
    let dd = match u16_at(optional, 0)? {
        0x10b => 96,
        0x20b => 112,
        _ => bail!("unknown PE optional header"),
    };
    let directory_count = u32_at(optional, dd - 4)? as usize;
    let headers_size = u32_at(optional, 60)? as usize;
    let sections = bytes(data, opt + opt_len, nsec * 40)?;
    let offset = |rva: u32, length: usize| -> Result<usize> {
        let address = rva as usize;
        if address < headers_size
            && address
                .checked_add(length)
                .is_some_and(|e| e <= headers_size)
        {
            bytes(data, address, length)?;
            return Ok(address);
        }
        for section in sections.chunks_exact(40) {
            let va = u32_at(section, 12)? as usize;
            let raw_size = u32_at(section, 16)? as usize;
            let raw = u32_at(section, 20)? as usize;
            // 仮想領域のゼロ埋め部分はファイルには存在しない。
            if let Some(delta) = address.checked_sub(va) {
                if delta.checked_add(length).is_some_and(|end| end <= raw_size) {
                    let at = raw.checked_add(delta).context("PE raw offset overflow")?;
                    bytes(data, at, length)?;
                    return Ok(at);
                }
            }
        }
        bail!("unmapped PE RVA 0x{rva:x}")
    };
    let mut tables = [Vec::new(), Vec::new()];
    for (target, (index, stride, name_field)) in tables.iter_mut().zip([(1, 20, 12), (13, 32, 4)]) {
        if directory_count <= index {
            continue;
        }
        let rva = u32_at(optional, dd + index * 8)?;
        let size = u32_at(optional, dd + index * 8 + 4)? as usize;
        if rva == 0 {
            continue;
        }
        ensure!(size >= stride, "invalid import directory size");
        let mut terminated = false;
        for i in 0..(size / stride).min(4096) {
            let descriptor_rva = rva
                .checked_add((i * stride) as u32)
                .context("import RVA overflow")?;
            let desc = bytes(data, offset(descriptor_rva, stride)?, stride)?;
            if desc.iter().all(|&b| b == 0) {
                terminated = true;
                break;
            }
            if index == 13 {
                ensure!(
                    u32_at(desc, 0)? & 1 != 0,
                    "legacy VA-based delay imports are unsupported"
                );
            }
            let name_rva = u32_at(desc, name_field)?;
            ensure!(name_rva != 0, "null import name");
            let mut name = Vec::new();
            for j in 0..512 {
                let at = name_rva.checked_add(j).context("name RVA overflow")?;
                let byte = data[offset(at, 1)?];
                if byte == 0 {
                    break;
                }
                ensure!(byte.is_ascii_graphic(), "non-ASCII DLL import");
                name.push(byte);
            }
            ensure!(
                !name.is_empty() && name.len() < 512,
                "invalid DLL import name"
            );
            target.push(String::from_utf8(name)?);
        }
        ensure!(terminated, "unterminated import directory");
    }
    let [regular, delay] = tables;
    Ok(Imports {
        machine,
        regular,
        delay,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture(delay: bool) -> Vec<u8> {
        let mut d = vec![0; 1024];
        d[..2].copy_from_slice(b"MZ");
        d[0x3c..0x40].copy_from_slice(&64u32.to_le_bytes());
        d[64..68].copy_from_slice(b"PE\0\0");
        d[68..70].copy_from_slice(&0x8664u16.to_le_bytes());
        d[70..72].copy_from_slice(&1u16.to_le_bytes());
        d[84..86].copy_from_slice(&240u16.to_le_bytes());
        d[88..90].copy_from_slice(&0x20bu16.to_le_bytes());
        d[148..152].copy_from_slice(&512u32.to_le_bytes());
        d[196..200].copy_from_slice(&16u32.to_le_bytes());
        let dir = 200 + if delay { 13 * 8 } else { 8 };
        d[dir..dir + 4].copy_from_slice(&4096u32.to_le_bytes());
        d[dir + 4..dir + 8].copy_from_slice(&64u32.to_le_bytes());
        for (off, value) in [(340, 4096u32), (344, 512), (348, 512)] {
            d[off..off + 4].copy_from_slice(&value.to_le_bytes());
        }
        let field = if delay { 516 } else { 524 };
        if delay {
            d[512] = 1;
        }
        d[field..field + 4].copy_from_slice(&4224u32.to_le_bytes());
        d[640..655].copy_from_slice(b"amdhip64_7.dll\0");
        d
    }

    #[test]
    fn reads_regular_and_delay_imports_and_rejects_truncation() {
        for delay in [false, true] {
            let data = fixture(delay);
            let parsed = parse(&data).unwrap();
            assert_eq!(parsed.family(), "rocm");
            assert_eq!(
                if delay {
                    &parsed.delay
                } else {
                    &parsed.regular
                },
                &["amdhip64_7.dll"]
            );
            for end in 0..655 {
                assert!(parse(&data[..end]).is_err());
            }
        }
    }

    #[test]
    fn distinguishes_cuda_unknown_and_mixed() {
        let mut p = Imports {
            machine: 0x8664,
            regular: vec!["cublas64_12.dll".into()],
            delay: vec![],
        };
        assert_eq!(p.family(), "cuda");
        p.delay.push("hipblas.dll".into());
        assert_eq!(p.family(), "mixed");
        p.regular.clear();
        p.delay.clear();
        assert_eq!(p.family(), "unknown");
    }

    #[cfg(windows)]
    #[test]
    fn parses_known_windows_dll() {
        let path =
            Path::new(&std::env::var_os("SystemRoot").unwrap()).join("System32/kernel32.dll");
        let imports = read(&path).unwrap();
        assert_eq!(imports.machine, 0x8664);
        assert!(!imports.regular.is_empty());
        assert_eq!(imports.family(), "unknown");
        assert!(imports
            .regular
            .iter()
            .any(|s| s.eq_ignore_ascii_case("ntdll.dll")));
    }
}
