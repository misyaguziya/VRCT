//! process.log and error.log (utils.setupLogger): "asctime - name - LEVEL - message" lines in the
//! working directory, truncated in place at 10 MB (TruncatingFileHandler: no numbered backups,
//! which Tauri's dev watcher would pick up).
use std::borrow::Cow;
use std::fs::{File, OpenOptions};
use std::io::{Seek, SeekFrom, Write};
use std::path::PathBuf;
use std::sync::Mutex;

const MAX_BYTES: u64 = 10 * 1024 * 1024;

pub struct LogFile {
    /// relative to the working directory, as the Python backend's
    file_name: Cow<'static, str>,
    name: &'static str,
    level: &'static str,
    // opened on the first write (delay=True)
    file: Mutex<Option<File>>,
}

/// logging's asctime: "2026-10-12 17:30:24,008"
pub fn asctime() -> String {
    chrono::Local::now().format("%Y-%m-%d %H:%M:%S,%3f").to_string()
}

impl LogFile {
    pub const fn new(file_name: &'static str, name: &'static str, level: &'static str) -> Self {
        Self { file_name: Cow::Borrowed(file_name), name, level, file: Mutex::new(None) }
    }

    /// A log at `path` (the chat log: logs/<start time>.log)
    pub fn at(path: String, name: &'static str, level: &'static str) -> Self {
        Self { file_name: Cow::Owned(path), name, level, file: Mutex::new(None) }
    }

    fn path(&self) -> PathBuf {
        PathBuf::from(&*self.file_name)
    }

    /// One record. A failure to write is dropped (the log must not stop the backend).
    pub fn write(&self, message: &str) {
        let line = format!("{} - {} - {} - {message}\n", asctime(), self.name, self.level);
        let mut file = self.file.lock().unwrap_or_else(|e| e.into_inner());
        if file.is_none() {
            *file = OpenOptions::new().create(true).append(true).open(self.path()).ok();
        }
        let Some(f) = file.as_mut() else { return };
        // shouldRollover: the record would reach maxBytes
        if f.seek(SeekFrom::End(0)).map(|end| end + line.len() as u64 >= MAX_BYTES).unwrap_or(false) {
            *file = File::create(self.path()).ok();
        }
        if let Some(f) = file.as_mut() {
            let _ = f.write_all(line.as_bytes());
            let _ = f.flush();
        }
    }

    /// removeLog: emptied (the start of each run)
    pub fn clear(&self) {
        let mut file = self.file.lock().unwrap_or_else(|e| e.into_inner());
        *file = None;
        let _ = File::create(self.path());
    }
}

pub static PROCESS: LogFile = LogFile::new("process.log", "process", "INFO");
pub static ERROR: LogFile = LogFile::new("error.log", "error", "ERROR");

/// errorLogging: what failed, in error.log (Rust has no traceback; the error's chain instead)
pub fn error(context: &str, error: &dyn std::fmt::Display) {
    ERROR.write(&format!("{context}: {error}"));
}
