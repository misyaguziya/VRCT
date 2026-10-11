//! The extension module `vrct_audio` for the Python backend (feature `python`).
use crate::energy::EnergyDetector;
use pyo3::{
    exceptions::{PyOverflowError, PyValueError},
    prelude::*,
    types::PyBytes,
};

#[pyfunction]
fn speaker_downmix_pcm16<'py>(py: Python<'py>, pcm: &Bound<'py, PyBytes>, channels: usize) -> PyResult<Bound<'py, PyBytes>> {
    let input = pcm.as_bytes();
    crate::validate_pcm(input.len(), channels).map_err(PyValueError::new_err)?;
    if channels < 3 {
        return Err(PyValueError::new_err("speaker downmix requires 3 to 256 channels"));
    }
    // The borrowed immutable bytes stay alive for this synchronous call.
    let output = py.allow_threads(|| crate::mix_speaker_frames(input, channels)).map_err(PyOverflowError::new_err)?;
    Ok(PyBytes::new(py, &output))
}

/// Encode mono PCM16LE to a complete FLAC stream without an external process.
#[pyfunction]
fn encode_flac<'py>(py: Python<'py>, pcm: &Bound<'py, PyBytes>, sample_rate: u32) -> PyResult<Bound<'py, PyBytes>> {
    let input = pcm.as_bytes();
    crate::validate_flac(input.len(), sample_rate).map_err(PyValueError::new_err)?;
    // PyBytes is immutable and its owner outlives the synchronous GIL release.
    let output = py.allow_threads(|| crate::encode_samples(input, sample_rate)).map_err(PyValueError::new_err)?;
    Ok(PyBytes::new(py, &output))
}

/// VAD downmix, deliberately different from the legacy speaker sum-and-clip.
#[pyfunction]
fn downmix_pcm16<'py>(py: Python<'py>, pcm: &Bound<'py, PyBytes>, channels: usize) -> PyResult<Bound<'py, PyBytes>> {
    let input = pcm.as_bytes();
    crate::validate_pcm(input.len(), channels).map_err(PyValueError::new_err)?;
    let output = py.allow_threads(|| crate::mix_frames(input, channels));
    Ok(PyBytes::new(py, &output))
}

/// Convert signed PCM8/16/24/32LE to mono PCM16LE. Drop incomplete channel frames.
#[pyfunction]
fn normalize_pcm16<'py>(py: Python<'py>, pcm: &Bound<'py, PyBytes>, sample_width: usize, channels: usize)
                        -> PyResult<Bound<'py, PyBytes>> {
    let input = pcm.as_bytes();
    crate::normalize::validate(input.len(), sample_width, channels).map_err(PyValueError::new_err)?;
    if sample_width == 2 && channels == 1 {
        // bytes is immutable; retain the Python reference without copying PCM.
        return Ok(pcm.clone());
    }
    let output = py.allow_threads(|| crate::normalize_pcm16(input, sample_width, channels)).map_err(PyValueError::new_err)?;
    Ok(PyBytes::new(py, &output))
}

#[pyfunction]
fn rms_pcm16(pcm: &Bound<'_, PyBytes>) -> PyResult<u32> {
    crate::rms(pcm.as_bytes()).map_err(PyValueError::new_err)
}

#[pyclass(name = "EnergyDetector")]
struct PyEnergyDetector(EnergyDetector);

#[pymethods]
impl PyEnergyDetector {
    #[new]
    #[pyo3(signature = (sample_rate, chunk, energy_threshold, dynamic=false, phrase_time_limit=0.0, record_timeout=f64::INFINITY, wait_timeout=1.0, pause_threshold=0.8, phrase_threshold=0.3, non_speaking_duration=0.5, damping=0.15, ratio=1.5))]
    // These parameters mirror existing Recognizer settings; no new app settings.
    #[allow(clippy::too_many_arguments)]
    fn new(sample_rate: u32, chunk: usize, energy_threshold: f64, dynamic: bool, phrase_time_limit: f64,
           record_timeout: f64, wait_timeout: f64, pause_threshold: f64, phrase_threshold: f64,
           non_speaking_duration: f64, damping: f64, ratio: f64) -> PyResult<Self> {
        EnergyDetector::new(sample_rate, chunk, energy_threshold, dynamic, phrase_time_limit, record_timeout,
                            wait_timeout, pause_threshold, phrase_threshold, non_speaking_duration, damping, ratio)
            .map(Self)
            .map_err(PyValueError::new_err)
    }

    #[getter]
    fn energy_threshold(&self) -> f64 {
        self.0.energy_threshold()
    }

    /// Called once before each read. RETRY is a listen boundary for pause handling.
    fn before_read<'py>(&mut self, py: Python<'py>, now: f64) -> PyResult<(&'static str, Option<Bound<'py, PyBytes>>)> {
        let (action, audio) = self.0.before_read(now).map_err(PyValueError::new_err)?;
        Ok((action, audio.map(|audio| PyBytes::new(py, &audio))))
    }

    /// PCM is interleaved for speakers, matching audioop.rms on the legacy input.
    fn push(&mut self, pcm: &Bound<'_, PyBytes>, now: f64) -> PyResult<u32> {
        self.0.push(pcm.as_bytes(), now).map_err(PyValueError::new_err)
    }

    fn calibrate(&mut self, energy: u32) {
        self.0.calibrate(energy)
    }

    #[getter]
    fn waiting(&self) -> bool {
        self.0.waiting()
    }

    fn cancel(&mut self) {
        self.0.cancel()
    }
}

// ---------------------------------------------------------------- devices (VRCT_RUST_AUDIO=1)
// Waits and stops run without the GIL: the COM / capture threads call back into Python.

use crate::devices::{self, Capture as RustCapture, DeviceInfo};
use crate::endpoints::{ActiveEndpointTracker as RustTracker, DeviceWatcher as RustWatcher, Flow};
use pyo3::exceptions::PyOSError;
use pyo3::types::PyDict;

/// A PortAudio-like device dict (the keys device_manager / the recorders read)
fn device_dict<'py>(py: Python<'py>, index: usize, d: &DeviceInfo, loopback: bool) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new(py);
    dict.set_item("index", index)?;
    dict.set_item("name", &d.name)?;
    dict.set_item("hostApi", 0)?;
    dict.set_item("maxInputChannels", d.channels)?;
    dict.set_item("maxOutputChannels", 0)?;
    dict.set_item("defaultSampleRate", d.sample_rate as f64)?;
    dict.set_item("isLoopbackDevice", loopback)?;
    Ok(dict)
}

/// {"inputs": [...], "loopbacks": [...], "default_input": name|None, "default_loopback": name|None}
#[pyfunction]
fn list_devices(py: Python<'_>) -> PyResult<Bound<'_, PyDict>> {
    let d = py.allow_threads(devices::list).map_err(PyOSError::new_err)?;
    let out = PyDict::new(py);
    let inputs = d.inputs.iter().enumerate().map(|(i, x)| device_dict(py, i, x, false)).collect::<PyResult<Vec<_>>>()?;
    let n = d.inputs.len();
    let loopbacks = d.loopbacks.iter().enumerate().map(|(i, x)| device_dict(py, n + i, x, true)).collect::<PyResult<Vec<_>>>()?;
    out.set_item("inputs", inputs)?;
    out.set_item("loopbacks", loopbacks)?;
    out.set_item("default_input", d.default_input)?;
    out.set_item("default_loopback", d.default_loopback)?;
    Ok(out)
}

/// A recording; the methods are the ones the Python code calls on a PyAudio stream
#[pyclass(name = "Capture")]
struct PyCapture(Option<RustCapture>);

impl PyCapture {
    fn get(&self) -> PyResult<&RustCapture> {
        self.0.as_ref().ok_or_else(|| PyOSError::new_err("the capture is closed"))
    }
}

#[pymethods]
impl PyCapture {
    /// `name`: an input, "<output> [Loopback]", or None for the default input
    #[new]
    #[pyo3(signature = (name=None))]
    fn new(py: Python<'_>, name: Option<String>) -> PyResult<Self> {
        let capture = py.allow_threads(|| RustCapture::open(name.as_deref())).map_err(PyOSError::new_err)?;
        Ok(Self(Some(capture)))
    }

    #[getter]
    fn sample_rate(&self) -> PyResult<u32> {
        Ok(self.get()?.sample_rate)
    }

    #[getter]
    fn channels(&self) -> PyResult<u16> {
        Ok(self.get()?.channels)
    }

    /// `frames` frames of PCM16; OSError when stopped or the device failed
    #[pyo3(signature = (frames, exception_on_overflow=false))]
    fn read<'py>(&self, py: Python<'py>, frames: usize, exception_on_overflow: bool) -> PyResult<Bound<'py, PyBytes>> {
        let _ = exception_on_overflow;
        let capture = self.get()?;
        let pcm = py.allow_threads(|| capture.read(frames, None)).map_err(PyOSError::new_err)?;
        Ok(PyBytes::new(py, &pcm.unwrap_or_default()))
    }

    fn get_read_available(&self) -> PyResult<usize> {
        Ok(self.get()?.available())
    }

    fn stop_stream(&self) -> PyResult<()> {
        self.get()?.stop();
        Ok(())
    }

    fn is_stopped(&self) -> bool {
        self.0.as_ref().is_none_or(|c| c.is_stopped())
    }

    fn close(&mut self, py: Python<'_>) {
        let capture = self.0.take();
        py.allow_threads(|| drop(capture));
    }
}

/// Calls `callback()` when an audio endpoint is added, removed, changes state or the default changes
#[pyclass(name = "DeviceWatcher")]
struct PyDeviceWatcher(Option<RustWatcher>);

#[pymethods]
impl PyDeviceWatcher {
    #[new]
    fn new(py: Python<'_>, callback: PyObject) -> PyResult<Self> {
        let call = move || Python::with_gil(|py| {
            if let Err(e) = callback.call0(py) {
                e.print(py);
            }
        });
        let watcher = py.allow_threads(|| RustWatcher::start(call)).map_err(PyOSError::new_err)?;
        Ok(Self(Some(watcher)))
    }

    fn stop(&mut self, py: Python<'_>) {
        let watcher = self.0.take();
        py.allow_threads(|| drop(watcher));
    }
}

/// ActiveEndpointTracker("render" | "capture") with the methods device_manager uses
#[pyclass(name = "ActiveEndpointTracker")]
struct PyTracker {
    flow: Flow,
    callback: Option<PyObject>,
    tracker: Option<RustTracker>,
}

#[pymethods]
impl PyTracker {
    #[new]
    #[pyo3(signature = (flow, com_lock=None))]
    fn new(flow: &str, com_lock: Option<PyObject>) -> PyResult<Self> {
        let _ = com_lock; // nothing to serialize with: cpal does not share PortAudio's state
        let flow = match flow {
            "render" => Flow::Render,
            "capture" => Flow::Capture,
            other => return Err(PyValueError::new_err(format!("flow must be 'render' or 'capture', got {other:?}"))),
        };
        Ok(Self { flow, callback: None, tracker: None })
    }

    fn set_on_change_callback(&mut self, cb: Option<PyObject>) {
        self.callback = cb;
    }

    fn start(&mut self, py: Python<'_>) {
        if self.tracker.is_some() {
            return;
        }
        let callback = self.callback.as_ref().map(|c| c.clone_ref(py));
        let on_change = move |name: Option<String>| {
            if let Some(cb) = &callback {
                Python::with_gil(|py| {
                    if let Err(e) = cb.call1(py, (name,)) {
                        e.print(py);
                    }
                });
            }
        };
        let flow = self.flow;
        self.tracker = Some(py.allow_threads(|| RustTracker::start(flow, on_change)));
    }

    /// True: stopped (the thread is joined)
    fn stop(&mut self, py: Python<'_>) -> bool {
        let tracker = self.tracker.take();
        py.allow_threads(|| drop(tracker));
        true
    }

    fn pause(&self) {
        if let Some(t) = &self.tracker {
            t.pause();
        }
    }

    fn resume(&self) {
        if let Some(t) = &self.tracker {
            t.resume();
        }
    }

    fn get_active_endpoint_name(&self) -> Option<String> {
        self.tracker.as_ref().and_then(|t| t.active_endpoint_name())
    }

    fn is_running(&self) -> bool {
        self.tracker.is_some()
    }

    fn is_stop_requested(&self) -> bool {
        false
    }

    #[pyo3(signature = (timeout=None))]
    fn wait_until_stopped(&self, timeout: Option<f64>) -> bool {
        let _ = timeout;
        self.tracker.is_none()
    }
}

#[pymodule]
fn vrct_audio(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(list_devices, m)?)?;
    m.add_class::<PyCapture>()?;
    m.add_class::<PyDeviceWatcher>()?;
    m.add_class::<PyTracker>()?;
    m.add_function(wrap_pyfunction!(encode_flac, m)?)?;
    m.add_function(wrap_pyfunction!(downmix_pcm16, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_pcm16, m)?)?;
    m.add_function(wrap_pyfunction!(speaker_downmix_pcm16, m)?)?;
    m.add_function(wrap_pyfunction!(rms_pcm16, m)?)?;
    m.add_class::<PyEnergyDetector>()?;
    Ok(())
}
