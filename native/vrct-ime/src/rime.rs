//! librime 1.17 (rime.dll, BSD-3) through its function table: `rime_get_api` returns RimeApi,
//! an int (its size) followed by function pointers in rime_api.h's order. The DLL is loaded at
//! run time from the folder given (the app's _internal).
use anyhow::{anyhow, bail, Context as _, Result};
use std::ffi::{c_char, c_int, c_void, CStr, CString};
use std::path::Path;
use windows_sys::Win32::Foundation::HMODULE;
use windows_sys::Win32::System::LibraryLoader::{GetProcAddress, LoadLibraryW};

type Bool = c_int;
type SessionId = usize;

/// RimeApi's functions by their place in rime_api.h (1 = setup), the ones used here
mod index {
    pub const SETUP: usize = 1;
    pub const INITIALIZE: usize = 3;
    pub const START_MAINTENANCE: usize = 5;
    pub const JOIN_MAINTENANCE_THREAD: usize = 7;
    pub const CREATE_SESSION: usize = 14;
    pub const DESTROY_SESSION: usize = 16;
    pub const PROCESS_KEY: usize = 19;
    pub const COMMIT_COMPOSITION: usize = 20;
    pub const CLEAR_COMPOSITION: usize = 21;
    pub const GET_COMMIT: usize = 22;
    pub const FREE_COMMIT: usize = 23;
    pub const GET_CONTEXT: usize = 24;
    pub const FREE_CONTEXT: usize = 25;
    pub const SET_OPTION: usize = 28;
    pub const SELECT_SCHEMA: usize = 35;
    pub const GET_INPUT: usize = 70;
    pub const GET_VERSION: usize = 73;
    pub const SELECT_CANDIDATE_ON_CURRENT_PAGE: usize = 75;
    pub const LAST: usize = SELECT_CANDIDATE_ON_CURRENT_PAGE;
}

/// X11 keysyms RIME takes besides the printable ASCII ones
pub mod keys {
    pub const BACKSPACE: i32 = 0xff08;
    pub const RETURN: i32 = 0xff0d;
    pub const LEFT: i32 = 0xff51;
    pub const RIGHT: i32 = 0xff53;
    pub const DOWN: i32 = 0xff54;
    pub const PAGE_UP: i32 = 0xff55;
    pub const PAGE_DOWN: i32 = 0xff56;
    pub const SPACE: i32 = 0x20;
}

#[repr(C)]
struct Traits {
    data_size: c_int,
    shared_data_dir: *const c_char,
    user_data_dir: *const c_char,
    distribution_name: *const c_char,
    distribution_code_name: *const c_char,
    distribution_version: *const c_char,
    app_name: *const c_char,
    modules: *const *const c_char,
    min_log_level: c_int,
    log_dir: *const c_char,
    prebuilt_data_dir: *const c_char,
    staging_dir: *const c_char,
}

#[repr(C)]
struct RawComposition {
    length: c_int,
    cursor_pos: c_int,
    sel_start: c_int,
    sel_end: c_int,
    preedit: *mut c_char,
}

#[repr(C)]
struct RawCandidate {
    text: *mut c_char,
    comment: *mut c_char,
    reserved: *mut c_void,
}

#[repr(C)]
struct RawMenu {
    page_size: c_int,
    page_no: c_int,
    is_last_page: Bool,
    highlighted_candidate_index: c_int,
    num_candidates: c_int,
    candidates: *mut RawCandidate,
    select_keys: *mut c_char,
}

#[repr(C)]
struct RawContext {
    data_size: c_int,
    composition: RawComposition,
    menu: RawMenu,
    commit_text_preview: *mut c_char,
    select_labels: *mut *mut c_char,
}

#[repr(C)]
struct RawCommit {
    data_size: c_int,
    text: *mut c_char,
}

/// A struct with RIME_STRUCT_INIT: zeroed, its data_size the size after that field
fn init<T>() -> T {
    let mut v: T = unsafe { std::mem::zeroed() };
    let size = (std::mem::size_of::<T>() - std::mem::size_of::<c_int>()) as c_int;
    unsafe { *(&mut v as *mut T as *mut c_int) = size };
    v
}

fn text(p: *const c_char) -> String {
    if p.is_null() {
        return String::new();
    }
    unsafe { CStr::from_ptr(p) }.to_string_lossy().into_owned()
}

fn wide(path: &Path) -> Vec<u16> {
    use std::os::windows::ffi::OsStrExt;
    path.as_os_str().encode_wide().chain(Some(0)).collect()
}

/// rime.dll and its function table
pub struct Rime {
    functions: *const *const c_void,
    _module: HMODULE,
}

// the table is read-only; RIME takes calls from any thread (one session at a time each)
unsafe impl Send for Rime {}
unsafe impl Sync for Rime {}

impl Rime {
    /// Loads `dll` (rime.dll) and reads its function table
    pub fn load(dll: &Path) -> Result<Rime> {
        let module = unsafe { LoadLibraryW(wide(dll).as_ptr()) };
        if module.is_null() {
            bail!("cannot load {}: {}", dll.display(), std::io::Error::last_os_error());
        }
        let get_api = unsafe { GetProcAddress(module, c"rime_get_api".as_ptr().cast()) }
            .with_context(|| format!("{} has no rime_get_api", dll.display()))?;
        let get_api: unsafe extern "C" fn() -> *const c_int = unsafe { std::mem::transmute(get_api) };
        let api = unsafe { get_api() };
        if api.is_null() {
            bail!("rime_get_api gave nothing");
        }
        // after the int, pointers are 8-aligned: the table holds data_size / 8 functions
        let count = (unsafe { *api } as usize).saturating_sub(4) / 8;
        if count < index::LAST {
            bail!("rime.dll's API has {count} functions, {} needed (librime 1.17 or later)", index::LAST);
        }
        let functions = unsafe { (api as *const u8).add(8) } as *const *const c_void;
        Ok(Rime { functions, _module: module })
    }

    /// The function at `i` (rime_api.h's order, 1 = setup), as `F`
    fn f<F: Copy>(&self, i: usize) -> F {
        let p = unsafe { *self.functions.add(i - 1) };
        assert!(!p.is_null(), "RimeApi function {i} is missing");
        unsafe { std::mem::transmute_copy(&p) }
    }

    pub fn version(&self) -> String {
        let f: unsafe extern "C" fn() -> *const c_char = self.f(index::GET_VERSION);
        text(unsafe { f() })
    }

    /// setup + initialize: the data in `shared` (schemas, dictionaries), what RIME builds and
    /// learns in `user`, its logs in `log_dir`. Once per process.
    pub fn start(&self, shared: &Path, user: &Path, log_dir: &Path) -> Result<()> {
        let c = |p: &Path| CString::new(p.to_string_lossy().as_bytes()).map_err(|_| anyhow!("NUL in {}", p.display()));
        let (shared, user, log_dir) = (c(shared)?, c(user)?, c(log_dir)?);
        let mut traits: Traits = init();
        traits.shared_data_dir = shared.as_ptr();
        traits.user_data_dir = user.as_ptr();
        traits.distribution_name = c"VRCT".as_ptr();
        traits.distribution_code_name = c"vrct".as_ptr();
        traits.distribution_version = c"1".as_ptr();
        traits.app_name = c"rime.vrct".as_ptr();
        traits.min_log_level = 2;
        traits.log_dir = log_dir.as_ptr();
        // RIME keeps the pointers: the strings live as long as the process
        std::mem::forget((shared, user, log_dir));
        let setup: unsafe extern "C" fn(*mut Traits) = self.f(index::SETUP);
        let initialize: unsafe extern "C" fn(*mut Traits) = self.f(index::INITIALIZE);
        unsafe {
            setup(&mut traits);
            initialize(&mut traits);
        }
        Ok(())
    }

    /// Builds what changed in the data (all of it the first time: ~15 s for Japanese and
    /// Chinese) and waits for it. `full_check`: look at every file, not only the changed times.
    pub fn deploy(&self, full_check: bool) -> bool {
        let start: unsafe extern "C" fn(Bool) -> Bool = self.f(index::START_MAINTENANCE);
        let join: unsafe extern "C" fn() = self.f(index::JOIN_MAINTENANCE_THREAD);
        let started = unsafe { start(full_check as Bool) } != 0;
        unsafe { join() };
        started
    }

    pub fn session(&self) -> Result<Session<'_>> {
        let create: unsafe extern "C" fn() -> SessionId = self.f(index::CREATE_SESSION);
        let id = unsafe { create() };
        if id == 0 {
            bail!("RIME made no session (not started?)");
        }
        Ok(Session { rime: self, id })
    }
}

/// What the keyboard shows: the composition and this page of candidates
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Context {
    pub preedit: String,
    /// the segment being converted, in `preedit`'s characters (not bytes)
    pub selection: (usize, usize),
    pub candidates: Vec<String>,
    pub highlighted: usize,
    pub page: usize,
    pub last_page: bool,
}

/// A byte offset of `s` as a character offset
fn chars_at(s: &str, byte: c_int) -> usize {
    let byte = (byte.max(0) as usize).min(s.len());
    s.char_indices().take_while(|(i, _)| *i < byte).count()
}

/// One input session (its composition, schema and options)
pub struct Session<'r> {
    rime: &'r Rime,
    id: SessionId,
}

impl Session<'_> {
    pub fn select_schema(&self, schema: &str) -> bool {
        let f: unsafe extern "C" fn(SessionId, *const c_char) -> Bool = self.rime.f(index::SELECT_SCHEMA);
        let schema = CString::new(schema).unwrap_or_default();
        unsafe { f(self.id, schema.as_ptr()) != 0 }
    }

    pub fn set_option(&self, option: &str, value: bool) {
        let f: unsafe extern "C" fn(SessionId, *const c_char, Bool) = self.rime.f(index::SET_OPTION);
        let option = CString::new(option).unwrap_or_default();
        unsafe { f(self.id, option.as_ptr(), value as Bool) }
    }

    /// A key (an ASCII character or a `keys` keysym); true when RIME took it
    pub fn key(&self, keycode: i32, mask: i32) -> bool {
        let f: unsafe extern "C" fn(SessionId, c_int, c_int) -> Bool = self.rime.f(index::PROCESS_KEY);
        unsafe { f(self.id, keycode, mask) != 0 }
    }

    /// The candidate at `index` of this page (a shorter one keeps the rest composing)
    pub fn select(&self, index: usize) -> bool {
        let f: unsafe extern "C" fn(SessionId, usize) -> Bool = self.rime.f(index::SELECT_CANDIDATE_ON_CURRENT_PAGE);
        unsafe { f(self.id, index) != 0 }
    }

    /// The composition as it is shown, committed (then taken with `take_commit`)
    pub fn commit_composition(&self) -> bool {
        let f: unsafe extern "C" fn(SessionId) -> Bool = self.rime.f(index::COMMIT_COMPOSITION);
        unsafe { f(self.id) != 0 }
    }

    pub fn clear(&self) {
        let f: unsafe extern "C" fn(SessionId) = self.rime.f(index::CLEAR_COMPOSITION);
        unsafe { f(self.id) }
    }

    /// The text RIME committed since the last call
    pub fn take_commit(&self) -> Option<String> {
        let get: unsafe extern "C" fn(SessionId, *mut RawCommit) -> Bool = self.rime.f(index::GET_COMMIT);
        let free: unsafe extern "C" fn(*mut RawCommit) -> Bool = self.rime.f(index::FREE_COMMIT);
        let mut commit: RawCommit = init();
        if unsafe { get(self.id, &mut commit) } == 0 {
            return None;
        }
        let out = text(commit.text);
        unsafe { free(&mut commit) };
        Some(out)
    }

    /// The keys typed so far (romaji / pinyin)
    pub fn input(&self) -> String {
        let f: unsafe extern "C" fn(SessionId) -> *const c_char = self.rime.f(index::GET_INPUT);
        text(unsafe { f(self.id) })
    }

    pub fn context(&self) -> Context {
        let get: unsafe extern "C" fn(SessionId, *mut RawContext) -> Bool = self.rime.f(index::GET_CONTEXT);
        let free: unsafe extern "C" fn(*mut RawContext) -> Bool = self.rime.f(index::FREE_CONTEXT);
        let mut raw: RawContext = init();
        if unsafe { get(self.id, &mut raw) } == 0 {
            return Context::default();
        }
        let preedit = text(raw.composition.preedit);
        let menu = &raw.menu;
        let candidates = (0..menu.num_candidates.max(0) as usize)
            .map(|i| text(unsafe { (*menu.candidates.add(i)).text }))
            .collect();
        let context = Context {
            selection: (chars_at(&preedit, raw.composition.sel_start), chars_at(&preedit, raw.composition.sel_end)),
            candidates,
            highlighted: menu.highlighted_candidate_index.max(0) as usize,
            page: menu.page_no.max(0) as usize,
            last_page: menu.is_last_page != 0,
            preedit,
        };
        unsafe { free(&mut raw) };
        context
    }
}

impl Drop for Session<'_> {
    fn drop(&mut self) {
        let f: unsafe extern "C" fn(SessionId) -> Bool = self.rime.f(index::DESTROY_SESSION);
        unsafe { f(self.id) };
    }
}
