//! The extension module (vrct_overlay) for the Python backend: the Rust overlay behind
//! models/overlay/rust_overlay.py (VRCT_RUST_OVERLAY=1), to check it in VR inside the running app.
//! It loads pyopenvr's openvr_api so both share one SteamVR connection, whose references are
//! counted here (openvr_session.py goes through acquire_session / release_session).
use crate::image::Image;
use crate::layout::{validate_tooltip, Layout, Region};
use crate::overlay::{Event, Overlay, Settings};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
use std::sync::{Arc, Mutex};

#[derive(Default)]
struct Callbacks {
    layout: Option<PyObject>,
    pointer: Option<PyObject>,
    position: Option<PyObject>,
    out_of_view: Option<PyObject>,
    intro: Option<PyObject>,
}

const POSITION_KEYS: [&str; 6] = ["x_pos", "y_pos", "z_pos", "x_rotation", "y_rotation", "z_rotation"];

fn settings_from(d: &Bound<'_, PyDict>) -> PyResult<Settings> {
    let number = |key: &str| -> PyResult<f64> {
        d.get_item(key)?.ok_or_else(|| PyValueError::new_err(format!("no {key}")))?.extract()
    };
    let mut position = [0.0; 6];
    for (value, key) in position.iter_mut().zip(POSITION_KEYS) {
        *value = number(key)?;
    }
    let panel_size = match (d.get_item("width")?, d.get_item("height")?) {
        (Some(w), Some(h)) => {
            let (w, h): (f64, f64) = (w.extract()?, h.extract()?);
            Some((w.round_ties_even() as u32, h.round_ties_even() as u32))
        }
        _ => None,
    };
    Ok(Settings {
        position,
        tracker: d.get_item("tracker")?.map_or(Ok("HMD".into()), |t| t.extract())?,
        opacity: number("opacity")?,
        ui_scaling: number("ui_scaling")?,
        display_duration: number("display_duration")?,
        fadeout_duration: number("fadeout_duration")?,
        panel_size,
    })
}

fn settings_dict<'py>(py: Python<'py>, s: &Settings, all: bool) -> PyResult<Bound<'py, PyDict>> {
    let d = PyDict::new(py);
    for (value, key) in s.position.iter().zip(POSITION_KEYS) {
        d.set_item(key, value)?;
    }
    d.set_item("ui_scaling", s.ui_scaling)?;
    d.set_item("tracker", &s.tracker)?;
    if all {
        d.set_item("opacity", s.opacity)?;
        d.set_item("display_duration", s.display_duration)?;
        d.set_item("fadeout_duration", s.fadeout_duration)?;
    }
    if let Some((w, h)) = s.panel_size {
        d.set_item("width", w)?;
        d.set_item("height", h)?;
    }
    Ok(d)
}

/// getVrLayout
fn layout_dict<'py>(py: Python<'py>, layout: &Layout, tooltip_epoch: u64) -> PyResult<Bound<'py, PyDict>> {
    let regions = PyDict::new(py);
    for region in Region::ALL {
        let [x, y, w, h] = layout.region(region);
        regions.set_item(region.name(), (x, y, w, h))?;
    }
    let d = PyDict::new(py);
    d.set_item("atlas", layout.atlas)?;
    d.set_item("regions", regions)?;
    d.set_item("tooltip_epoch", tooltip_epoch)?;
    Ok(d)
}

/// A request from Python as JSON (bools stay bools, ints ints: the checks tell them apart)
fn to_json(value: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    use serde_json::Value;
    Ok(if value.is_none() {
        Value::Null
    } else if value.is_instance_of::<PyBool>() {
        Value::Bool(value.extract()?)
    } else if value.is_instance_of::<PyInt>() {
        match value.extract::<i64>() {
            Ok(v) => Value::from(v),
            // too large for the checks anyway
            Err(_) => Value::from(f64::MAX),
        }
    } else if value.is_instance_of::<PyFloat>() {
        serde_json::Number::from_f64(value.extract()?).map_or(Value::Null, Value::Number)
    } else if value.is_instance_of::<PyString>() {
        Value::String(value.extract()?)
    } else if let Ok(d) = value.downcast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (k, v) in d.iter() {
            map.insert(k.extract()?, to_json(&v)?);
        }
        Value::Object(map)
    } else if value.is_instance_of::<PyList>() || value.is_instance_of::<PyTuple>() {
        Value::Array(value.try_iter()?.map(|v| to_json(&v?)).collect::<PyResult<_>>()?)
    } else {
        return Err(PyValueError::new_err("not JSON"));
    })
}

fn call<'py>(py: Python<'py>, callback: Option<PyObject>, args: impl IntoPyObject<'py, Target = PyTuple>) {
    let Some(callback) = callback else { return };
    if let Err(e) = callback.call1(py, args) {
        // as overlay.py's errorLogging: a failing callback does not stop the overlay
        e.print(py);
    }
}

fn dispatch(callbacks: &Mutex<Callbacks>, event: Event) {
    Python::with_gil(|py| {
        // taken out first: a callback may set callbacks
        let take = |f: fn(&Callbacks) -> &Option<PyObject>| f(&callbacks.lock().unwrap()).as_ref().map(|c| c.clone_ref(py));
        let result: PyResult<()> = (|| {
            match event {
                Event::Layout { layout, tooltip_epoch } => call(py, take(|c| &c.layout), (layout_dict(py, &layout, tooltip_epoch)?,)),
                Event::Pointer(xy) => call(py, take(|c| &c.pointer), (xy,)),
                Event::Position { size, settings } => call(py, take(|c| &c.position), (size, settings_dict(py, &settings, false)?)),
                Event::PanelOutOfView(out) => call(py, take(|c| &c.out_of_view), (out,)),
                Event::LauncherIntro(intro) => call(py, take(|c| &c.intro), (intro.name(),)),
            }
            Ok(())
        })();
        if let Err(e) = result {
            e.print(py);
        }
    });
}

#[pyclass(name = "Overlay", module = "vrct_overlay")]
struct PyOverlay {
    overlay: Mutex<Overlay>,
    callbacks: Arc<Mutex<Callbacks>>,
}

impl PyOverlay {
    fn with<T>(&self, f: impl FnOnce(&mut Overlay) -> T) -> T {
        f(&mut self.overlay.lock().unwrap())
    }
}

#[pymethods]
impl PyOverlay {
    /// settings: {size: overlay settings dict}, in the order of the overlay keys; log(line)
    #[new]
    fn new(settings: &Bound<'_, PyDict>, log: PyObject) -> PyResult<Self> {
        let mut sizes = vec![];
        for (name, value) in settings.iter() {
            sizes.push((name.extract::<String>()?, settings_from(value.downcast()?)?));
        }
        let callbacks = Arc::new(Mutex::new(Callbacks::default()));
        let events = callbacks.clone();
        let overlay = Overlay::new(
            sizes,
            Arc::new(move |line| Python::with_gil(|py| call(py, Some(log.clone_ref(py)), (line,)))),
            Arc::new(move |event| dispatch(&events, event)),
        );
        Ok(Self { overlay: Mutex::new(overlay), callbacks })
    }

    /// name: "layout", "pointer", "position", "out_of_view", "intro"; None to remove
    fn set_callback(&self, name: &str, callback: Option<PyObject>) -> PyResult<()> {
        let mut c = self.callbacks.lock().unwrap();
        let slot = match name {
            "layout" => &mut c.layout,
            "pointer" => &mut c.pointer,
            "position" => &mut c.position,
            "out_of_view" => &mut c.out_of_view,
            "intro" => &mut c.intro,
            _ => return Err(PyValueError::new_err(format!("no callback {name}"))),
        };
        *slot = callback;
        Ok(())
    }

    fn start(&self) {
        self.with(Overlay::start);
    }

    /// Waits for the overlay thread (up to 5 s) without the GIL: it may need it for a callback
    fn stop(&self, py: Python<'_>) {
        py.allow_threads(|| self.with(Overlay::stop));
    }

    #[getter]
    fn initialized(&self) -> bool {
        self.with(|o| o.shared().initialized)
    }

    #[getter]
    fn launcher_intro_state(&self) -> &'static str {
        self.with(|o| o.shared().intro.name())
    }

    /// The settings as the overlay thread last published them
    fn settings<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let shared = self.with(|o| o.shared());
        let d = PyDict::new(py);
        for (name, s) in &shared.settings {
            d.set_item(name, settings_dict(py, s, true)?)?;
        }
        Ok(d)
    }

    fn vr_layout<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let shared = self.with(|o| o.shared());
        layout_dict(py, &shared.layout, shared.tooltip_epoch)
    }

    /// RGBA bytes, width x height
    fn update_image(&self, size: &str, width: usize, height: usize, rgba: Vec<u8>) -> PyResult<()> {
        if width == 0 || height == 0 || rgba.len() != width * height * 4 {
            return Err(PyValueError::new_err("image size"));
        }
        self.with(|o| o.update_image(size, Image { width, height, data: rgba }));
        Ok(())
    }

    fn clear_image(&self, size: &str) {
        self.with(|o| o.clear_image(size));
    }

    fn update_opacity(&self, size: &str, opacity: f64, with_fade: bool) {
        self.with(|o| o.update_opacity(size, opacity, with_fade));
    }

    fn update_ui_scaling(&self, size: &str, ui_scaling: f64) {
        self.with(|o| o.update_ui_scaling(size, ui_scaling));
    }

    fn update_position(&self, size: &str, position: [f64; 6], tracker: &str) {
        self.with(|o| o.update_position(size, position, tracker));
    }

    fn update_display_duration(&self, size: &str, seconds: f64) {
        self.with(|o| o.update_display_duration(size, seconds));
    }

    fn update_fadeout_duration(&self, size: &str, seconds: f64) {
        self.with(|o| o.update_fadeout_duration(size, seconds));
    }

    fn set_vr_windows(&self, log: bool, popup: bool) {
        self.with(|o| o.set_vr_windows(log, popup));
    }

    fn set_vr_panel_enabled(&self, enabled: bool) {
        self.with(|o| o.set_vr_panel_enabled(enabled));
    }

    fn set_panel_locked(&self, locked: bool) {
        self.with(|o| o.set_panel_locked(locked));
    }

    fn set_launcher_auto_hide(&self, enabled: bool) {
        self.with(|o| o.set_launcher_auto_hide(enabled));
    }

    fn set_launcher_defaults(&self, settings: &Bound<'_, PyDict>) -> PyResult<()> {
        let settings = settings_from(settings)?;
        self.with(|o| o.set_launcher_defaults(settings));
        Ok(())
    }

    fn reset_launcher(&self, keep_hand: bool) {
        self.with(|o| o.reset_launcher(keep_hand));
    }

    fn request_anchor(&self, anchor: &str) {
        self.with(|o| o.request_anchor(anchor));
    }

    fn recall_panel(&self) {
        self.with(|o| o.recall_panel());
    }

    /// ValueError (the reason) for a malformed request, as overlay_tooltip.validate_tooltip
    fn set_tooltip(&self, data: &Bound<'_, PyAny>) -> PyResult<()> {
        let tooltip = validate_tooltip(&to_json(data)?).map_err(PyValueError::new_err)?;
        self.with(|o| o.set_tooltip(tooltip));
        Ok(())
    }

    fn set_layout_rendered(&self, panel_size: (u32, u32)) {
        self.with(|o| o.set_layout_rendered(panel_size));
    }
}

static SESSIONS: Mutex<Vec<vrct_openvr::Session>> = Mutex::new(Vec::new());

/// pyopenvr's openvr_api (its path), before anything here uses OpenVR
#[pyfunction]
fn use_openvr_dll(path: std::path::PathBuf) -> bool {
    vrct_openvr::use_dll(path)
}

/// openvr_session.acquire: a reference to the shared session (application_type: EVRApplicationType)
#[pyfunction]
fn acquire_session(application_type: i32) -> PyResult<()> {
    let kind = if application_type == vrct_openvr::ApplicationType::Overlay as i32 {
        vrct_openvr::ApplicationType::Overlay
    } else {
        vrct_openvr::ApplicationType::Background
    };
    let session = vrct_openvr::acquire(kind).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    SESSIONS.lock().unwrap().push(session);
    Ok(())
}

/// openvr_session.release (nothing without a matching acquire)
#[pyfunction]
fn release_session() {
    let session = SESSIONS.lock().unwrap().pop();
    drop(session);
}

#[pymodule]
fn vrct_overlay(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyOverlay>()?;
    m.add_function(wrap_pyfunction!(use_openvr_dll, m)?)?;
    m.add_function(wrap_pyfunction!(acquire_session, m)?)?;
    m.add_function(wrap_pyfunction!(release_session, m)?)?;
    Ok(())
}
