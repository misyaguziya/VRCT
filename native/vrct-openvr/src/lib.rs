//! OpenVR for VRCT: Valve's openvr_api 1.26.7 (`openvr_api.dll` next to the executable; the same
//! file pyopenvr 1.26.701 ships, so the interfaces are the Python backend's), called through the C
//! function tables (`FnTable:IVROverlay_027` ...) with only the functions VRCT uses, in safe wrappers.
//! Not the openvr / openvr_sys crates: those build SDK 2.x from source (CMake and libclang) and move
//! to newer interface versions.
//!
//! `acquire` is the process-wide, reference-counted session (models/openvr_session.py):
//! VR_Shutdown tears down the whole process's connection, so the overlay, OCR and the clipboard
//! share one and the last `Session` dropped shuts it down.
use std::ffi::{c_char, c_void, CStr, CString};
use std::sync::{Mutex, OnceLock};
use windows_sys::Win32::System::LibraryLoader::{GetProcAddress, LoadLibraryW};

pub mod tables;

pub const MAX_TRACKED_DEVICE_COUNT: usize = 64;
pub const TRACKED_DEVICE_INDEX_HMD: u32 = 0;
pub const TRACKED_DEVICE_INDEX_INVALID: u32 = 0xFFFF_FFFF;

/// EVRApplicationType
#[derive(Clone, Copy, Debug, PartialEq)]
#[repr(i32)]
pub enum ApplicationType {
    Overlay = 2,
    Background = 3,
}

/// ETrackingUniverseOrigin
pub const TRACKING_UNIVERSE_STANDING: i32 = 1;
/// ETrackedControllerRole
pub const CONTROLLER_ROLE_LEFT_HAND: i32 = 1;
pub const CONTROLLER_ROLE_RIGHT_HAND: i32 = 2;
/// ETextureType / EColorSpace
pub const TEXTURE_TYPE_DIRECTX: i32 = 0;
pub const COLOR_SPACE_AUTO: i32 = 0;
pub const COLOR_SPACE_GAMMA: i32 = 1;
/// EVREventType
pub const EVENT_QUIT: u32 = 700;
/// EVRButtonId (bit numbers)
pub const BUTTON_GRIP: u32 = 2;
pub const BUTTON_STEAMVR_TRIGGER: u32 = 33;
/// EDeviceActivityLevel
pub const ACTIVITY_UNKNOWN: i32 = -1;
pub const ACTIVITY_USER_INTERACTION: i32 = 1;
pub const ACTIVITY_USER_INTERACTION_TIMEOUT: i32 = 2;
/// ETrackedDeviceProperty / EVRApplicationProperty
pub const PROP_RENDER_MODEL_NAME_STRING: u32 = 1003;
pub const APPLICATION_PROPERTY_NAME_STRING: u32 = 0;
/// EVREye
pub const EYE_LEFT: i32 = 0;
pub const EYE_RIGHT: i32 = 1;

pub type HmdMatrix34 = [[f32; 4]; 3];

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct TrackedDevicePose {
    pub device_to_absolute_tracking: HmdMatrix34,
    pub velocity: [f32; 3],
    pub angular_velocity: [f32; 3],
    pub tracking_result: i32,
    pub pose_is_valid: bool,
    pub device_is_connected: bool,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct ControllerState {
    pub packet_num: u32,
    pub button_pressed: u64,
    pub button_touched: u64,
    pub axis: [[f32; 2]; 5],
}

/// VREvent_t: the data union is kept as raw bytes
#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct Event {
    pub event_type: u32,
    pub tracked_device_index: u32,
    pub event_age_seconds: f32,
    pub data: [u64; 6],
}

#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct Texture {
    pub handle: *mut c_void,
    pub texture_type: i32,
    pub color_space: i32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct TextureBounds {
    pub u_min: f32,
    pub v_min: f32,
    pub u_max: f32,
    pub v_max: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct IntersectionParams {
    pub source: [f32; 3],
    pub direction: [f32; 3],
    pub origin: i32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct IntersectionResults {
    pub point: [f32; 3],
    pub normal: [f32; 3],
    pub uvs: [f32; 2],
    pub distance: f32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct ComponentState {
    pub tracking_to_component_render_model: HmdMatrix34,
    pub tracking_to_component_local: HmdMatrix34,
    pub properties: u32,
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct ControllerModeState {
    pub scroll_wheel_visible: bool,
}

/// An OpenVR error code (EVRInitError, EVROverlayError, ...) with what it is called
#[derive(Clone, Debug, PartialEq)]
pub struct Error {
    pub code: i32,
    pub message: String,
}

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} (error number {})", self.message, self.code)
    }
}

impl std::error::Error for Error {}

fn err(code: impl Into<i64>, what: &str) -> Error {
    let code = code.into() as i32;
    Error { code, message: what.into() }
}

struct Api {
    init: unsafe extern "C" fn(*mut i32, i32, *const c_char) -> u32,
    shutdown: unsafe extern "C" fn(),
    interface: unsafe extern "C" fn(*const c_char, *mut i32) -> *mut c_void,
    init_error_description: unsafe extern "C" fn(i32) -> *const c_char,
}

/// openvr_api.dll from the executable's folder, once
fn api() -> Result<&'static Api, Error> {
    static API: OnceLock<Result<Api, Error>> = OnceLock::new();
    API.get_or_init(|| unsafe {
        let exe = std::env::current_exe().map_err(|e| err(-1, &e.to_string()))?;
        let path = exe.parent().map(|d| d.join("openvr_api.dll")).ok_or_else(|| err(-1, "no executable folder"))?;
        let wide: Vec<u16> = path.as_os_str().encode_wide_null();
        let module = LoadLibraryW(wide.as_ptr());
        if module.is_null() {
            return Err(err(-1, &format!("cannot load {}", path.display())));
        }
        let get = |name: &CStr| GetProcAddress(module, name.as_ptr() as *const u8).ok_or_else(|| err(-1, &format!("{name:?} missing")));
        Ok(Api {
            init: std::mem::transmute::<unsafe extern "system" fn() -> isize, _>(get(c"VR_InitInternal2")?),
            shutdown: std::mem::transmute::<unsafe extern "system" fn() -> isize, _>(get(c"VR_ShutdownInternal")?),
            interface: std::mem::transmute::<unsafe extern "system" fn() -> isize, _>(get(c"VR_GetGenericInterface")?),
            init_error_description: std::mem::transmute::<unsafe extern "system" fn() -> isize, _>(
                get(c"VR_GetVRInitErrorAsEnglishDescription")?),
        })
    }).as_ref().map_err(Clone::clone)
}

trait WideNull {
    fn encode_wide_null(&self) -> Vec<u16>;
}

impl WideNull for std::ffi::OsStr {
    fn encode_wide_null(&self) -> Vec<u16> {
        use std::os::windows::ffi::OsStrExt;
        self.encode_wide().chain([0]).collect()
    }
}

/// The reference count of the process's session
static SESSION: Mutex<usize> = Mutex::new(0);

/// A reference to the shared OpenVR session (openvr_session.acquire); dropping it releases it
pub struct Session(());

/// openvr.init(application_type) for the first caller, a new reference for the others
pub fn acquire(application_type: ApplicationType) -> Result<Session, Error> {
    let api = api()?;
    let mut count = SESSION.lock().unwrap();
    if *count == 0 {
        let mut error = 0;
        unsafe { (api.init)(&mut error, application_type as i32, std::ptr::null()) };
        if error != 0 {
            let message = unsafe { CStr::from_ptr((api.init_error_description)(error)) }.to_string_lossy().into_owned();
            return Err(Error { code: error, message });
        }
    }
    *count += 1;
    Ok(Session(()))
}

pub fn is_active() -> bool {
    *SESSION.lock().unwrap() > 0
}

impl Drop for Session {
    fn drop(&mut self) {
        let mut count = SESSION.lock().unwrap();
        *count -= 1;
        if *count == 0 {
            if let Ok(api) = api() {
                unsafe { (api.shutdown)() };
            }
        }
    }
}

/// An interface's function table (valid while a Session lives)
struct Table<'s> {
    functions: *const usize,
    _session: std::marker::PhantomData<&'s Session>,
}

impl Session {
    fn table(&self, version: &str, len: usize) -> Result<Table<'_>, Error> {
        let name = CString::new(format!("FnTable:{version}")).unwrap();
        let mut error = 0;
        let functions = unsafe { (api()?.interface)(name.as_ptr(), &mut error) } as *const usize;
        if error != 0 || functions.is_null() {
            return Err(err(error, &format!("{version} is not available")));
        }
        let _ = len;
        Ok(Table { functions, _session: std::marker::PhantomData })
    }

    pub fn system(&self) -> Result<System<'_>, Error> {
        Ok(System(self.table(tables::system::VERSION, tables::system::LEN)?))
    }

    pub fn overlay(&self) -> Result<Overlay<'_>, Error> {
        Ok(Overlay(self.table(tables::overlay::VERSION, tables::overlay::LEN)?))
    }

    pub fn compositor(&self) -> Result<Compositor<'_>, Error> {
        Ok(Compositor(self.table(tables::compositor::VERSION, tables::compositor::LEN)?))
    }

    pub fn applications(&self) -> Result<Applications<'_>, Error> {
        Ok(Applications(self.table(tables::applications::VERSION, tables::applications::LEN)?))
    }

    pub fn render_models(&self) -> Result<RenderModels<'_>, Error> {
        Ok(RenderModels(self.table(tables::render_models::VERSION, tables::render_models::LEN)?))
    }
}

impl Table<'_> {
    /// The function at `index`, as `F` (an `unsafe extern "C" fn` of the right signature)
    unsafe fn f<F: Copy>(&self, index: usize) -> F {
        unsafe {
            let address = *self.functions.add(index);
            std::mem::transmute_copy::<usize, F>(&address)
        }
    }
}

/// A string through the two-call pattern (size first, then the text)
fn read_string(call: impl Fn(*mut c_char, u32) -> u32) -> String {
    let size = call(std::ptr::null_mut(), 0);
    if size == 0 {
        return String::new();
    }
    let mut buf = vec![0u8; size as usize];
    call(buf.as_mut_ptr() as *mut c_char, size);
    CStr::from_bytes_until_nul(&buf).map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()
}

pub struct System<'s>(Table<'s>);

impl System<'_> {
    pub fn device_to_absolute_tracking_pose(&self, origin: i32, predicted_seconds: f32) -> Vec<TrackedDevicePose> {
        let mut poses = vec![TrackedDevicePose::default(); MAX_TRACKED_DEVICE_COUNT];
        unsafe {
            let f: unsafe extern "C" fn(i32, f32, *mut TrackedDevicePose, u32) = self.0.f(tables::system::GET_DEVICE_TO_ABSOLUTE_TRACKING_POSE);
            f(origin, predicted_seconds, poses.as_mut_ptr(), poses.len() as u32);
        }
        poses
    }

    pub fn tracked_device_index_for_controller_role(&self, role: i32) -> u32 {
        unsafe {
            let f: unsafe extern "C" fn(i32) -> u32 = self.0.f(tables::system::GET_TRACKED_DEVICE_INDEX_FOR_CONTROLLER_ROLE);
            f(role)
        }
    }

    pub fn controller_state(&self, index: u32) -> Option<ControllerState> {
        let mut state = ControllerState::default();
        let ok = unsafe {
            let f: unsafe extern "C" fn(u32, *mut ControllerState, u32) -> bool = self.0.f(tables::system::GET_CONTROLLER_STATE);
            f(index, &mut state, size_of::<ControllerState>() as u32)
        };
        ok.then_some(state)
    }

    pub fn poll_next_event(&self) -> Option<Event> {
        let mut event = Event::default();
        let ok = unsafe {
            let f: unsafe extern "C" fn(*mut Event, u32) -> bool = self.0.f(tables::system::POLL_NEXT_EVENT);
            f(&mut event, size_of::<Event>() as u32)
        };
        ok.then_some(event)
    }

    pub fn string_tracked_device_property(&self, index: u32, property: u32) -> String {
        read_string(|buf, size| unsafe {
            let f: unsafe extern "C" fn(u32, u32, *mut c_char, u32, *mut i32) -> u32 =
                self.0.f(tables::system::GET_STRING_TRACKED_DEVICE_PROPERTY);
            let mut error = 0;
            f(index, property, buf, size, &mut error)
        })
    }

    pub fn tracked_device_activity_level(&self, index: u32) -> i32 {
        unsafe {
            let f: unsafe extern "C" fn(u32) -> i32 = self.0.f(tables::system::GET_TRACKED_DEVICE_ACTIVITY_LEVEL);
            f(index)
        }
    }

    pub fn is_tracked_device_connected(&self, index: u32) -> bool {
        unsafe {
            let f: unsafe extern "C" fn(u32) -> bool = self.0.f(tables::system::IS_TRACKED_DEVICE_CONNECTED);
            f(index)
        }
    }

    /// The DXGI adapter index of the headset (for the D3D11 device that shares textures with SteamVR)
    pub fn dxgi_output_info(&self) -> i32 {
        let mut adapter = -1;
        unsafe {
            let f: unsafe extern "C" fn(*mut i32) = self.0.f(tables::system::GET_DXGI_OUTPUT_INFO);
            f(&mut adapter);
        }
        adapter
    }
}

pub struct Overlay<'s>(Table<'s>);

/// EVROverlayError to Result
fn overlay_result(code: u32, what: &str) -> Result<(), Error> {
    if code == 0 { Ok(()) } else { Err(err(code, what)) }
}

impl Overlay<'_> {
    pub fn create_overlay(&self, key: &str, name: &str) -> Result<u64, Error> {
        let (key_c, name_c) = (CString::new(key).unwrap(), CString::new(name).unwrap());
        let mut handle = 0;
        let code = unsafe {
            let f: unsafe extern "C" fn(*const c_char, *const c_char, *mut u64) -> u32 = self.0.f(tables::overlay::CREATE_OVERLAY);
            f(key_c.as_ptr(), name_c.as_ptr(), &mut handle)
        };
        overlay_result(code, &format!("CreateOverlay {key}")).map(|()| handle)
    }

    pub fn find_overlay(&self, key: &str) -> Result<u64, Error> {
        let key_c = CString::new(key).unwrap();
        let mut handle = 0;
        let code = unsafe {
            let f: unsafe extern "C" fn(*const c_char, *mut u64) -> u32 = self.0.f(tables::overlay::FIND_OVERLAY);
            f(key_c.as_ptr(), &mut handle)
        };
        overlay_result(code, &format!("FindOverlay {key}")).map(|()| handle)
    }

    fn handle_call(&self, index: usize, handle: u64, what: &str) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64) -> u32 = self.0.f(index);
            f(handle)
        };
        overlay_result(code, what)
    }

    pub fn destroy_overlay(&self, handle: u64) -> Result<(), Error> {
        self.handle_call(tables::overlay::DESTROY_OVERLAY, handle, "DestroyOverlay")
    }

    pub fn show_overlay(&self, handle: u64) -> Result<(), Error> {
        self.handle_call(tables::overlay::SHOW_OVERLAY, handle, "ShowOverlay")
    }

    pub fn hide_overlay(&self, handle: u64) -> Result<(), Error> {
        self.handle_call(tables::overlay::HIDE_OVERLAY, handle, "HideOverlay")
    }

    pub fn clear_overlay_texture(&self, handle: u64) -> Result<(), Error> {
        self.handle_call(tables::overlay::CLEAR_OVERLAY_TEXTURE, handle, "ClearOverlayTexture")
    }

    pub fn is_overlay_visible(&self, handle: u64) -> bool {
        unsafe {
            let f: unsafe extern "C" fn(u64) -> bool = self.0.f(tables::overlay::IS_OVERLAY_VISIBLE);
            f(handle)
        }
    }

    pub fn set_overlay_texture(&self, handle: u64, texture: &Texture) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, *const Texture) -> u32 = self.0.f(tables::overlay::SET_OVERLAY_TEXTURE);
            f(handle, texture)
        };
        overlay_result(code, "SetOverlayTexture")
    }

    /// RGBA pixels (`bytes_per_pixel` 4) copied into the overlay
    pub fn set_overlay_raw(&self, handle: u64, pixels: &[u8], width: u32, height: u32, bytes_per_pixel: u32) -> Result<(), Error> {
        assert_eq!(pixels.len(), (width * height * bytes_per_pixel) as usize);
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, *const c_void, u32, u32, u32) -> u32 = self.0.f(tables::overlay::SET_OVERLAY_RAW);
            f(handle, pixels.as_ptr() as *const c_void, width, height, bytes_per_pixel)
        };
        overlay_result(code, "SetOverlayRaw")
    }

    fn handle_f32(&self, index: usize, handle: u64, value: f32, what: &str) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, f32) -> u32 = self.0.f(index);
            f(handle, value)
        };
        overlay_result(code, what)
    }

    pub fn set_overlay_width_in_meters(&self, handle: u64, meters: f32) -> Result<(), Error> {
        self.handle_f32(tables::overlay::SET_OVERLAY_WIDTH_IN_METERS, handle, meters, "SetOverlayWidthInMeters")
    }

    pub fn set_overlay_alpha(&self, handle: u64, alpha: f32) -> Result<(), Error> {
        self.handle_f32(tables::overlay::SET_OVERLAY_ALPHA, handle, alpha, "SetOverlayAlpha")
    }

    pub fn set_overlay_color(&self, handle: u64, red: f32, green: f32, blue: f32) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, f32, f32, f32) -> u32 = self.0.f(tables::overlay::SET_OVERLAY_COLOR);
            f(handle, red, green, blue)
        };
        overlay_result(code, "SetOverlayColor")
    }

    pub fn set_overlay_sort_order(&self, handle: u64, order: u32) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, u32) -> u32 = self.0.f(tables::overlay::SET_OVERLAY_SORT_ORDER);
            f(handle, order)
        };
        overlay_result(code, "SetOverlaySortOrder")
    }

    pub fn set_overlay_transform_absolute(&self, handle: u64, origin: i32, transform: &HmdMatrix34) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, i32, *const HmdMatrix34) -> u32 = self.0.f(tables::overlay::SET_OVERLAY_TRANSFORM_ABSOLUTE);
            f(handle, origin, transform)
        };
        overlay_result(code, "SetOverlayTransformAbsolute")
    }

    pub fn set_overlay_transform_tracked_device_relative(&self, handle: u64, device: u32, transform: &HmdMatrix34) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, u32, *const HmdMatrix34) -> u32 =
                self.0.f(tables::overlay::SET_OVERLAY_TRANSFORM_TRACKED_DEVICE_RELATIVE);
            f(handle, device, transform)
        };
        overlay_result(code, "SetOverlayTransformTrackedDeviceRelative")
    }

    pub fn set_overlay_texture_bounds(&self, handle: u64, bounds: &TextureBounds) -> Result<(), Error> {
        let code = unsafe {
            let f: unsafe extern "C" fn(u64, *const TextureBounds) -> u32 = self.0.f(tables::overlay::SET_OVERLAY_TEXTURE_BOUNDS);
            f(handle, bounds)
        };
        overlay_result(code, "SetOverlayTextureBounds")
    }

    pub fn compute_overlay_intersection(&self, handle: u64, params: &IntersectionParams) -> Option<IntersectionResults> {
        let mut results = IntersectionResults::default();
        let hit = unsafe {
            let f: unsafe extern "C" fn(u64, *const IntersectionParams, *mut IntersectionResults) -> bool =
                self.0.f(tables::overlay::COMPUTE_OVERLAY_INTERSECTION);
            f(handle, params, &mut results)
        };
        hit.then_some(results)
    }
}

pub struct Compositor<'s>(Table<'s>);

impl Compositor<'_> {
    /// The compositor's mirror of `eye` as a shader resource view on `device` (ID3D11Device*)
    pub fn mirror_texture_d3d11(&self, eye: i32, device: *mut c_void) -> Result<*mut c_void, Error> {
        let mut view = std::ptr::null_mut();
        let code = unsafe {
            let f: unsafe extern "C" fn(i32, *mut c_void, *mut *mut c_void) -> u32 = self.0.f(tables::compositor::GET_MIRROR_TEXTURE_D3D11);
            f(eye, device, &mut view)
        };
        if code != 0 {
            return Err(err(code, "GetMirrorTextureD3D11"));
        }
        if view.is_null() {
            return Err(err(-1, "GetMirrorTextureD3D11 returned null"));
        }
        Ok(view)
    }

    pub fn release_mirror_texture_d3d11(&self, view: *mut c_void) {
        unsafe {
            let f: unsafe extern "C" fn(*mut c_void) = self.0.f(tables::compositor::RELEASE_MIRROR_TEXTURE_D3D11);
            f(view)
        }
    }

    pub fn last_frame_renderer(&self) -> u32 {
        unsafe {
            let f: unsafe extern "C" fn() -> u32 = self.0.f(tables::compositor::GET_LAST_FRAME_RENDERER);
            f()
        }
    }

    pub fn current_scene_focus_process(&self) -> u32 {
        unsafe {
            let f: unsafe extern "C" fn() -> u32 = self.0.f(tables::compositor::GET_CURRENT_SCENE_FOCUS_PROCESS);
            f()
        }
    }
}

pub struct Applications<'s>(Table<'s>);

impl Applications<'_> {
    pub fn application_count(&self) -> u32 {
        unsafe {
            let f: unsafe extern "C" fn() -> u32 = self.0.f(tables::applications::GET_APPLICATION_COUNT);
            f()
        }
    }

    pub fn application_key_by_index(&self, index: u32) -> String {
        // the key buffer size comes from k_unMaxApplicationKeyLength
        let mut buf = vec![0u8; 128];
        unsafe {
            let f: unsafe extern "C" fn(u32, *mut c_char, u32) -> i32 = self.0.f(tables::applications::GET_APPLICATION_KEY_BY_INDEX);
            f(index, buf.as_mut_ptr() as *mut c_char, buf.len() as u32);
        }
        CStr::from_bytes_until_nul(&buf).map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()
    }

    pub fn application_property_string(&self, key: &str, property: u32) -> String {
        let key_c = CString::new(key).unwrap();
        read_string(|buf, size| unsafe {
            let f: unsafe extern "C" fn(*const c_char, u32, *mut c_char, u32, *mut i32) -> u32 =
                self.0.f(tables::applications::GET_APPLICATION_PROPERTY_STRING);
            let mut error = 0;
            f(key_c.as_ptr(), property, buf, size, &mut error)
        })
    }
}

pub struct RenderModels<'s>(Table<'s>);

impl RenderModels<'_> {
    pub fn component_state(&self, model: &str, component: &str, state: &ControllerState, mode: &ControllerModeState)
                           -> Option<ComponentState> {
        let (model_c, component_c) = (CString::new(model).unwrap(), CString::new(component).unwrap());
        let mut result = ComponentState::default();
        let ok = unsafe {
            let f: unsafe extern "C" fn(*const c_char, *const c_char, *const ControllerState, *const ControllerModeState,
                                        *mut ComponentState) -> bool = self.0.f(tables::render_models::GET_COMPONENT_STATE);
            f(model_c.as_ptr(), component_c.as_ptr(), state, mode, &mut result)
        };
        ok.then_some(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::mem::{offset_of, size_of};

    /// The structures are laid out as pyopenvr's ctypes ones (tables::LAYOUTS)
    #[test]
    fn layouts_match_pyopenvr() {
        let ours: &[(&str, usize, Vec<usize>)] = &[
            ("HmdMatrix34_t", size_of::<HmdMatrix34>(), vec![0]),
            ("TrackedDevicePose_t", size_of::<TrackedDevicePose>(), vec![
                offset_of!(TrackedDevicePose, device_to_absolute_tracking), offset_of!(TrackedDevicePose, velocity),
                offset_of!(TrackedDevicePose, angular_velocity), offset_of!(TrackedDevicePose, tracking_result),
                offset_of!(TrackedDevicePose, pose_is_valid), offset_of!(TrackedDevicePose, device_is_connected)]),
            ("VRControllerState_t", size_of::<ControllerState>(), vec![
                offset_of!(ControllerState, packet_num), offset_of!(ControllerState, button_pressed),
                offset_of!(ControllerState, button_touched), offset_of!(ControllerState, axis)]),
            ("VREvent_t", size_of::<Event>(), vec![
                offset_of!(Event, event_type), offset_of!(Event, tracked_device_index),
                offset_of!(Event, event_age_seconds), offset_of!(Event, data)]),
            ("Texture_t", size_of::<Texture>(), vec![
                offset_of!(Texture, handle), offset_of!(Texture, texture_type), offset_of!(Texture, color_space)]),
            ("VRTextureBounds_t", size_of::<TextureBounds>(), vec![0, 4, 8, 12]),
            ("VROverlayIntersectionParams_t", size_of::<IntersectionParams>(), vec![
                offset_of!(IntersectionParams, source), offset_of!(IntersectionParams, direction), offset_of!(IntersectionParams, origin)]),
            ("VROverlayIntersectionResults_t", size_of::<IntersectionResults>(), vec![
                offset_of!(IntersectionResults, point), offset_of!(IntersectionResults, normal),
                offset_of!(IntersectionResults, uvs), offset_of!(IntersectionResults, distance)]),
            ("RenderModel_ComponentState_t", size_of::<ComponentState>(), vec![
                offset_of!(ComponentState, tracking_to_component_render_model),
                offset_of!(ComponentState, tracking_to_component_local), offset_of!(ComponentState, properties)]),
            ("RenderModel_ControllerMode_State_t", size_of::<ControllerModeState>(), vec![0]),
        ];
        for (name, size, offsets) in ours {
            let (_, expected_size, fields) = tables::LAYOUTS.iter().find(|l| l.0 == *name).unwrap();
            assert_eq!(size, expected_size, "{name} size");
            let expected: Vec<usize> = fields.iter().map(|f| f.1).collect();
            assert_eq!(offsets, &expected, "{name} offsets");
        }
    }
}
