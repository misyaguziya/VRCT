//! Stage-1 PoC (docs/rust_backend_migration_plan_2026-10-07.md): capture a window
//! into a Rust-owned D3D11 texture whose pointer Python hands to SteamVR.
//! OpenVR stays in Python; this module never initializes or shuts it down.
use pyo3::{
    exceptions::PyRuntimeError,
    prelude::*,
    types::{PyBytes, PyDict},
};
pub mod capture;

fn error(context: &str, err: windows::core::Error) -> PyErr {
    PyRuntimeError::new_err(format!(
        "{context}: {err} (HRESULT 0x{:08X})",
        err.code().0 as u32
    ))
}

/// One capture session. Bound to the creating thread (`unsendable`): COM and the
/// immediate D3D11 context must not be used from another thread.
#[pyclass(unsendable)]
struct CaptureSession {
    inner: Option<capture::Capture>,
}

impl CaptureSession {
    fn get(&self) -> PyResult<&capture::Capture> {
        self.inner
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("capture session is closed"))
    }
}

#[pymethods]
impl CaptureSession {
    #[new]
    #[pyo3(signature = (hwnd, adapter_index, width, height, shared=false))]
    fn new(
        hwnd: isize,
        adapter_index: u32,
        width: u32,
        height: u32,
        shared: bool,
    ) -> PyResult<Self> {
        if width == 0 || height == 0 || width > 16384 || height > 16384 {
            return Err(PyRuntimeError::new_err("texture size must be 1..=16384"));
        }
        let inner = capture::Capture::new(hwnd, adapter_index, width, height, shared)
            .map_err(|e| error("CaptureSession", e))?;
        Ok(Self { inner: Some(inner) })
    }

    /// ID3D11Texture2D* borrowed for Texture_t.handle; valid until close().
    #[getter]
    fn texture_ptr(&self) -> PyResult<usize> {
        Ok(self.get()?.texture_ptr())
    }

    #[getter]
    fn size(&self) -> PyResult<(u32, u32)> {
        Ok(self.get()?.size())
    }

    /// Copy the newest frame's client box (left, top, right, bottom) into the texture.
    /// Returns None when no new frame arrived. Never waits.
    fn poll<'py>(
        &mut self,
        py: Python<'py>,
        client_box: (u32, u32, u32, u32),
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        let inner = self
            .inner
            .as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("capture session is closed"))?;
        let Some(polled) = inner.poll(client_box).map_err(|e| error("poll", e))? else {
            return Ok(None);
        };
        let out = PyDict::new(py);
        out.set_item("frame_id", polled.frame_id)?;
        out.set_item("content", polled.content)?;
        out.set_item("copied", polled.copied)?;
        out.set_item("system_time_100ns", polled.system_time_100ns)?;
        Ok(Some(out))
    }

    /// PoC check only: the texture as BGRA bytes (width * height * 4).
    fn read_back<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let pixels = self.get()?.read_back().map_err(|e| error("read_back", e))?;
        Ok(PyBytes::new(py, &pixels))
    }

    /// Stop capturing and release the texture. Idempotent. Unset the texture on every
    /// overlay that uses it before calling this.
    fn close(&mut self) {
        self.inner = None;
    }

    #[getter]
    fn closed(&self) -> bool {
        self.inner.is_none()
    }
}

#[pymodule]
fn vrct_graphics(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CaptureSession>()
}
