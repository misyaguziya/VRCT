//! The extension module (vrct_graphics.CaptureSession) for the Python backend
use pyo3::{
    exceptions::{PyRuntimeError, PyValueError},
    prelude::*,
    types::{PyBytes, PyDict},
};
use crate::capture;

fn windows_error(context: &str, err: windows::core::Error) -> PyErr {
    PyRuntimeError::new_err(format!(
        "{context}: {err} (HRESULT 0x{:08X})",
        err.code().0 as u32
    ))
}

fn error(context: &str, err: capture::Error) -> PyErr {
    match err {
        capture::Error::Windows(err) => windows_error(context, err),
        capture::Error::Invalid(message) => PyValueError::new_err(format!("{context}: {message}")),
    }
}

/// GPU resources for one VR panel texture. Bound to the creating thread (`unsendable`):
/// COM and the immediate D3D11 context must not be used from another thread. Call
/// close() on that thread: PyO3 does not run Drop for an unsendable object collected
/// elsewhere, so the D3D11 objects would leak.
#[pyclass(unsendable)]
struct CaptureSession {
    inner: Option<capture::Gpu>,
}

impl CaptureSession {
    fn gpu(&self) -> PyResult<&capture::Gpu> {
        self.inner
            .as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("capture session is closed"))
    }

    fn gpu_mut(&mut self) -> PyResult<&mut capture::Gpu> {
        self.inner
            .as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("capture session is closed"))
    }
}

#[pymethods]
impl CaptureSession {
    #[new]
    fn new(adapter_index: u32, width: u32, height: u32) -> PyResult<Self> {
        if width == 0 || height == 0 || width > 16384 || height > 16384 {
            return Err(PyValueError::new_err("texture size must be 1..=16384"));
        }
        let inner = capture::Gpu::new(adapter_index, width, height)
            .map_err(|e| windows_error("CaptureSession", e))?;
        Ok(Self { inner: Some(inner) })
    }

    /// Start (or restart) Windows.Graphics.Capture of a top-level window.
    fn start(&mut self, hwnd: isize) -> PyResult<()> {
        self.gpu_mut()?
            .start(hwnd)
            .map_err(|e| windows_error("start", e))
    }

    /// Stop capturing; the textures stay valid. Idempotent.
    fn stop(&mut self) -> PyResult<()> {
        self.gpu_mut()?.stop();
        Ok(())
    }

    #[getter]
    fn capturing(&self) -> PyResult<bool> {
        Ok(self.gpu()?.capturing())
    }

    /// Copy the newest frame's client box (left, top, right, bottom) into the captured
    /// texture. Returns None when no new frame arrived (or not capturing). Never waits.
    fn poll<'py>(
        &mut self,
        py: Python<'py>,
        client_box: (u32, u32, u32, u32),
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        let Some(polled) = self
            .gpu_mut()?
            .poll(client_box)
            .map_err(|e| windows_error("poll", e))?
        else {
            return Ok(None);
        };
        let out = PyDict::new(py);
        out.set_item("frame_id", polled.frame_id)?;
        out.set_item("frame", polled.frame)?;
        out.set_item("copied", polled.copied)?;
        out.set_item("system_time_100ns", polled.system_time_100ns)?;
        Ok(Some(out))
    }

    /// PrintWindow fallback: copy the client box of a BGRA frame into the captured texture.
    fn upload(
        &self,
        raw: &[u8],
        frame_width: u32,
        frame_height: u32,
        client_box: (u32, u32, u32, u32),
    ) -> PyResult<(u32, u32)> {
        self.gpu()?
            .upload(raw, (frame_width, frame_height), client_box)
            .map_err(|e| error("upload", e))
    }

    /// One BGRA row of the captured texture (texture width * 4 bytes): tooltip marker check.
    fn read_row<'py>(&self, py: Python<'py>, y: u32) -> PyResult<Bound<'py, PyBytes>> {
        let row = self.gpu()?.read_row(y).map_err(|e| error("read_row", e))?;
        Ok(PyBytes::new(py, &row))
    }

    /// Alpha mask for the image area (width * height bytes); its size is the render area.
    fn set_mask(&mut self, data: &[u8], width: u32, height: u32) -> PyResult<()> {
        self.gpu_mut()?
            .set_mask(data, width, height)
            .map_err(|e| error("set_mask", e))
    }

    /// Compose captured x mask into the overlay texture. intro: 0 idle, 1 pending, 2 playing;
    /// launcher_rect is (x0, y0, x1, y1) in pixels.
    #[pyo3(signature = (intro=0, launcher_rect=(0, 0, 0, 0)))]
    fn render(&self, intro: u32, launcher_rect: (i32, i32, i32, i32)) -> PyResult<()> {
        self.gpu()?
            .render(intro, launcher_rect)
            .map_err(|e| error("render", e))
    }

    /// Send queued GPU work now. Call after SetOverlayTexture: SteamVR records its copy of
    /// the texture on this device's context, and without a flush that copy waits for the next
    /// render (seen in VR: every change showed one update late, a tooltip only after a click).
    fn flush(&self) -> PyResult<()> {
        self.gpu()?.flush();
        Ok(())
    }

    /// ID3D11Texture2D* borrowed for Texture_t.handle; valid until close().
    #[getter]
    fn texture_ptr(&self) -> PyResult<usize> {
        Ok(self.gpu()?.texture_ptr())
    }

    #[getter]
    fn size(&self) -> PyResult<(u32, u32)> {
        Ok(self.gpu()?.size())
    }

    /// Tests only: the overlay texture as BGRA bytes (width * height * 4).
    fn read_back<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let pixels = self
            .gpu()?
            .read_back()
            .map_err(|e| windows_error("read_back", e))?;
        Ok(PyBytes::new(py, &pixels))
    }

    /// Stop capturing and release the textures. Idempotent. Clear the texture on every
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
