//! VR UI image path on the GPU, on a chosen DXGI adapter (SteamVR's).
//!
//! `captured` receives the client box of each Windows.Graphics.Capture frame
//! (or PrintWindow bytes via `upload`); `render` composes it with a CPU-built
//! mask (and the launcher intro keying) into `out`, the texture SteamVR reads.
//! No CPU copy of whole frames on the normal path: `read_row` reads one row
//! for the tooltip marker, `read_back` exists for tests only. Everything runs
//! on the caller's thread, except that WGC frames are taken from the
//! free-threaded pool as they arrive (on a WinRT thread) and only the newest
//! is kept until `poll`.
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex, MutexGuard,
};
use windows::{
    core::{Interface, Result},
    Foundation::TypedEventHandler,
    Graphics::{
        Capture::{
            Direct3D11CaptureFrame, Direct3D11CaptureFramePool, GraphicsCaptureItem,
            GraphicsCaptureSession,
        },
        DirectX::{Direct3D11::IDirect3DDevice, DirectXPixelFormat},
        SizeInt32,
    },
    Win32::{
        Foundation::{HMODULE, HWND},
        Graphics::{
            Direct3D::{D3D_DRIVER_TYPE_UNKNOWN, D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST},
            Direct3D11::{
                D3D11CreateDevice, ID3D11Buffer, ID3D11Device, ID3D11DeviceContext,
                ID3D11PixelShader, ID3D11RenderTargetView, ID3D11ShaderResourceView,
                ID3D11Texture2D, ID3D11VertexShader, D3D11_BIND_CONSTANT_BUFFER,
                D3D11_BIND_RENDER_TARGET, D3D11_BIND_SHADER_RESOURCE, D3D11_BOX, D3D11_BUFFER_DESC,
                D3D11_CPU_ACCESS_READ, D3D11_CREATE_DEVICE_BGRA_SUPPORT, D3D11_MAPPED_SUBRESOURCE,
                D3D11_MAP_READ, D3D11_SDK_VERSION, D3D11_SUBRESOURCE_DATA, D3D11_TEXTURE2D_DESC,
                D3D11_USAGE_DEFAULT, D3D11_USAGE_STAGING, D3D11_VIEWPORT,
            },
            Dxgi::{
                Common::{
                    DXGI_FORMAT, DXGI_FORMAT_B8G8R8A8_UNORM, DXGI_FORMAT_R8_UNORM, DXGI_SAMPLE_DESC,
                },
                CreateDXGIFactory1, IDXGIDevice, IDXGIFactory1,
            },
        },
        System::WinRT::{
            Direct3D11::{CreateDirect3D11DeviceFromDXGIDevice, IDirect3DDxgiInterfaceAccess},
            Graphics::Capture::IGraphicsCaptureItemInterop,
            RoInitialize, RO_INIT_MULTITHREADED,
        },
    },
};

const FORMAT: DirectXPixelFormat = DirectXPixelFormat::B8G8R8A8UIntNormalized;
const BUFFERS: i32 = 2;
const VS: &[u8] = include_bytes!("../shaders/compose_vs.cso");
const PS: &[u8] = include_bytes!("../shaders/compose_ps.cso");

pub enum Error {
    Windows(windows::core::Error),
    Invalid(&'static str),
}

impl From<windows::core::Error> for Error {
    fn from(err: windows::core::Error) -> Self {
        Self::Windows(err)
    }
}

/// Copy box for the client rectangle inside a frame, clipped to both textures.
/// Returns None when nothing would be copied.
pub fn copy_box(
    client: (u32, u32, u32, u32),
    frame: (u32, u32),
    owned: (u32, u32),
) -> Option<D3D11_BOX> {
    let (left, top, right, bottom) = client;
    let right = right.min(frame.0);
    let bottom = bottom.min(frame.1);
    if left >= right || top >= bottom {
        return None;
    }
    let width = (right - left).min(owned.0);
    let height = (bottom - top).min(owned.1);
    Some(D3D11_BOX {
        left,
        top,
        front: 0,
        right: left + width,
        bottom: top + height,
        back: 1,
    })
}

pub struct Polled {
    pub frame_id: u64,
    pub frame: (u32, u32),
    pub copied: (u32, u32),
    pub system_time_100ns: i64,
}

#[repr(C)]
struct Params {
    intro: u32,
    pad: [u32; 3],
    rect: [i32; 4],
}

struct Wgc {
    item: GraphicsCaptureItem,
    pool: Direct3D11CaptureFramePool,
    session: GraphicsCaptureSession,
    pool_size: SizeInt32,
    // Set from a WinRT thread when the window goes away or capture ends.
    closed: Arc<AtomicBool>,
    closed_token: i64,
    // The newest frame, replaced from a WinRT thread as frames arrive. Left in the
    // pool instead, both buffers fill between polls and WGC holds back the last
    // change until the next poll (measured: every poll after a burst of changes
    // returned the one before last), so a hover tooltip waited for the next change.
    newest: Arc<Mutex<Option<Direct3D11CaptureFrame>>>,
    arrived_token: i64,
}

fn lock(
    slot: &Mutex<Option<Direct3D11CaptureFrame>>,
) -> MutexGuard<'_, Option<Direct3D11CaptureFrame>> {
    slot.lock().unwrap_or_else(|poisoned| poisoned.into_inner())
}

impl Drop for Wgc {
    fn drop(&mut self) {
        let _ = self.pool.RemoveFrameArrived(self.arrived_token);
        let _ = self.item.RemoveClosed(self.closed_token);
        let _ = self.session.Close();
        if let Some(frame) = lock(&self.newest).take() {
            let _ = frame.Close();
        }
        let _ = self.pool.Close();
    }
}

struct Mask {
    texture: ID3D11Texture2D,
    view: ID3D11ShaderResourceView,
    size: (u32, u32),
}

pub struct Gpu {
    device: ID3D11Device,
    context: ID3D11DeviceContext,
    winrt_device: IDirect3DDevice,
    captured: ID3D11Texture2D,
    captured_view: ID3D11ShaderResourceView,
    out: ID3D11Texture2D,
    out_target: ID3D11RenderTargetView,
    row: ID3D11Texture2D,
    vs: ID3D11VertexShader,
    ps: ID3D11PixelShader,
    params: ID3D11Buffer,
    mask: Option<Mask>,
    size: (u32, u32),
    wgc: Option<Wgc>,
    frame_id: u64,
}

fn texture_desc(size: (u32, u32), format: DXGI_FORMAT, bind: u32) -> D3D11_TEXTURE2D_DESC {
    D3D11_TEXTURE2D_DESC {
        Width: size.0,
        Height: size.1,
        MipLevels: 1,
        ArraySize: 1,
        Format: format,
        SampleDesc: DXGI_SAMPLE_DESC {
            Count: 1,
            Quality: 0,
        },
        Usage: D3D11_USAGE_DEFAULT,
        BindFlags: bind,
        CPUAccessFlags: 0,
        MiscFlags: 0,
    }
}

fn staging_desc(size: (u32, u32)) -> D3D11_TEXTURE2D_DESC {
    D3D11_TEXTURE2D_DESC {
        Usage: D3D11_USAGE_STAGING,
        CPUAccessFlags: D3D11_CPU_ACCESS_READ.0 as u32,
        ..texture_desc(size, DXGI_FORMAT_B8G8R8A8_UNORM, 0)
    }
}

impl Gpu {
    pub fn new(adapter_index: u32, width: u32, height: u32) -> Result<Self> {
        // An apartment set up by someone else (RPC_E_CHANGED_MODE) is fine for a free-threaded pool.
        let _ = unsafe { RoInitialize(RO_INIT_MULTITHREADED) };
        let factory: IDXGIFactory1 = unsafe { CreateDXGIFactory1()? };
        let adapter = unsafe { factory.EnumAdapters1(adapter_index)? };
        let (mut device, mut context) = (None, None);
        unsafe {
            D3D11CreateDevice(
                &adapter,
                D3D_DRIVER_TYPE_UNKNOWN,
                HMODULE::default(),
                D3D11_CREATE_DEVICE_BGRA_SUPPORT,
                None,
                D3D11_SDK_VERSION,
                Some(&mut device),
                None,
                Some(&mut context),
            )?;
        }
        let device: ID3D11Device = device.expect("D3D11CreateDevice returned no device");
        let context = context.expect("D3D11CreateDevice returned no context");
        let dxgi: IDXGIDevice = device.cast()?;
        let winrt_device: IDirect3DDevice =
            unsafe { CreateDirect3D11DeviceFromDXGIDevice(&dxgi)? }.cast()?;

        let size = (width, height);
        // Start fully transparent so a region never shows stale GPU memory.
        let zeros = vec![0u8; width as usize * height as usize * 4];
        let init = D3D11_SUBRESOURCE_DATA {
            pSysMem: zeros.as_ptr().cast(),
            SysMemPitch: width * 4,
            SysMemSlicePitch: 0,
        };
        let shader = D3D11_BIND_SHADER_RESOURCE.0 as u32;
        let (mut captured, mut out, mut row) = (None, None, None);
        let (mut captured_view, mut out_target) = (None, None);
        let (mut vs, mut ps, mut params) = (None, None, None);
        unsafe {
            device.CreateTexture2D(
                &texture_desc(size, DXGI_FORMAT_B8G8R8A8_UNORM, shader),
                Some(&init),
                Some(&mut captured),
            )?;
            let out_bind = shader | D3D11_BIND_RENDER_TARGET.0 as u32;
            device.CreateTexture2D(
                &texture_desc(size, DXGI_FORMAT_B8G8R8A8_UNORM, out_bind),
                Some(&init),
                Some(&mut out),
            )?;
            device.CreateTexture2D(&staging_desc((width, 1)), None, Some(&mut row))?;
            device.CreateShaderResourceView(
                captured.as_ref().unwrap(),
                None,
                Some(&mut captured_view),
            )?;
            device.CreateRenderTargetView(out.as_ref().unwrap(), None, Some(&mut out_target))?;
            device.CreateVertexShader(VS, None, Some(&mut vs))?;
            device.CreatePixelShader(PS, None, Some(&mut ps))?;
            let desc = D3D11_BUFFER_DESC {
                ByteWidth: std::mem::size_of::<Params>() as u32,
                Usage: D3D11_USAGE_DEFAULT,
                BindFlags: D3D11_BIND_CONSTANT_BUFFER.0 as u32,
                ..Default::default()
            };
            device.CreateBuffer(&desc, None, Some(&mut params))?;
        }
        Ok(Self {
            device,
            context,
            winrt_device,
            captured: captured.unwrap(),
            captured_view: captured_view.unwrap(),
            out: out.unwrap(),
            out_target: out_target.unwrap(),
            row: row.unwrap(),
            vs: vs.unwrap(),
            ps: ps.unwrap(),
            params: params.unwrap(),
            mask: None,
            size,
            wgc: None,
            frame_id: 0,
        })
    }

    pub fn texture_ptr(&self) -> usize {
        self.out.as_raw() as usize
    }

    pub fn size(&self) -> (u32, u32) {
        self.size
    }

    pub fn capturing(&self) -> bool {
        self.wgc
            .as_ref()
            .is_some_and(|wgc| !wgc.closed.load(Ordering::Relaxed))
    }

    /// Start (or restart) capturing a window. The textures stay; only WGC changes.
    pub fn start(&mut self, hwnd: isize) -> Result<()> {
        self.wgc = None;
        let interop = windows::core::factory::<GraphicsCaptureItem, IGraphicsCaptureItemInterop>()?;
        let item: GraphicsCaptureItem = unsafe { interop.CreateForWindow(HWND(hwnd as _))? };
        let pool_size = item.Size()?;
        let pool = Direct3D11CaptureFramePool::CreateFreeThreaded(
            &self.winrt_device,
            FORMAT,
            BUFFERS,
            pool_size,
        )?;
        let session = pool.CreateCaptureSession(&item)?;
        let closed = Arc::new(AtomicBool::new(false));
        let flag = closed.clone();
        let closed_token = item.Closed(&TypedEventHandler::new(move |_, _| {
            flag.store(true, Ordering::Relaxed);
            Ok(())
        }))?;
        let newest = Arc::new(Mutex::new(None));
        let slot = newest.clone();
        let arrived_token = pool.FrameArrived(&TypedEventHandler::new(
            move |pool: windows::core::Ref<Direct3D11CaptureFramePool>, _| {
                if let Ok(pool) = pool.ok() {
                    let mut slot = lock(&slot);
                    while let Ok(frame) = pool.TryGetNextFrame() {
                        if let Some(old) = slot.replace(frame) {
                            old.Close()?;
                        }
                    }
                }
                Ok(())
            },
        ))?;
        let wgc = Wgc {
            item,
            pool,
            session,
            pool_size,
            closed,
            closed_token,
            newest,
            arrived_token,
        };
        wgc.session.SetIsCursorCaptureEnabled(false)?;
        // Not available before Windows 11: then the yellow border stays.
        let _ = wgc.session.SetIsBorderRequired(false);
        wgc.session.StartCapture()?;
        self.wgc = Some(wgc);
        Ok(())
    }

    pub fn stop(&mut self) {
        self.wgc = None;
    }

    /// Copies the newest WGC frame (if any arrived) into `captured`. Never waits.
    pub fn poll(&mut self, client: (u32, u32, u32, u32)) -> Result<Option<Polled>> {
        let Some(wgc) = self.wgc.as_mut() else {
            return Ok(None);
        };
        let Some(frame) = lock(&wgc.newest).take() else {
            return Ok(None);
        };
        // Return the frame to the pool even when copying fails half way.
        let copied = self.copy_frame(&frame, client);
        let closed = frame.Close();
        let (content, desc, copied, system_time_100ns) = copied?;
        closed?;
        let Some(wgc) = self.wgc.as_mut() else {
            return Ok(None);
        };
        // A minimized window reports 0x0: keep the pool until it has a size again.
        let resized =
            content.Width != wgc.pool_size.Width || content.Height != wgc.pool_size.Height;
        if resized && content.Width > 0 && content.Height > 0 {
            // The window was resized: later frames come at the new size.
            wgc.pool
                .Recreate(&self.winrt_device, FORMAT, BUFFERS, content)?;
            wgc.pool_size = content;
        }
        self.frame_id += 1;
        Ok(Some(Polled {
            frame_id: self.frame_id,
            frame: (desc.Width, desc.Height),
            copied,
            system_time_100ns,
        }))
    }

    fn copy_frame(
        &self,
        frame: &Direct3D11CaptureFrame,
        client: (u32, u32, u32, u32),
    ) -> Result<(SizeInt32, D3D11_TEXTURE2D_DESC, (u32, u32), i64)> {
        let content = frame.ContentSize()?;
        let surface = frame.Surface()?;
        let access: IDirect3DDxgiInterfaceAccess = surface.cast()?;
        let texture: ID3D11Texture2D = unsafe { access.GetInterface()? };
        let mut desc = D3D11_TEXTURE2D_DESC::default();
        unsafe { texture.GetDesc(&mut desc) };
        let copied = match copy_box(client, (desc.Width, desc.Height), self.size) {
            Some(region) => {
                unsafe {
                    self.context.CopySubresourceRegion(
                        &self.captured,
                        0,
                        0,
                        0,
                        0,
                        &texture,
                        0,
                        Some(&region),
                    )
                };
                (region.right - region.left, region.bottom - region.top)
            }
            None => (0, 0),
        };
        let system_time_100ns = frame.SystemRelativeTime()?.Duration;
        Ok((content, desc, copied, system_time_100ns))
    }

    /// PrintWindow fallback: copy the client box of a BGRA frame into `captured`.
    pub fn upload(
        &self,
        raw: &[u8],
        frame: (u32, u32),
        client: (u32, u32, u32, u32),
    ) -> std::result::Result<(u32, u32), Error> {
        if frame.0 == 0
            || frame.1 == 0
            || frame.0 > 16384
            || frame.1 > 16384
            || raw.len() as u64 != frame.0 as u64 * frame.1 as u64 * 4
        {
            return Err(Error::Invalid(
                "raw must be frame_width * frame_height * 4 BGRA bytes",
            ));
        }
        let region = copy_box(client, frame, self.size)
            .ok_or(Error::Invalid("client box is outside the frame"))?;
        let (width, height) = (region.right - region.left, region.bottom - region.top);
        let start = (region.top as usize * frame.0 as usize + region.left as usize) * 4;
        let target = D3D11_BOX {
            left: 0,
            top: 0,
            front: 0,
            right: width,
            bottom: height,
            back: 1,
        };
        unsafe {
            self.context.UpdateSubresource(
                &self.captured,
                0,
                Some(&target),
                raw[start..].as_ptr().cast(),
                frame.0 * 4,
                0,
            );
        }
        Ok((width, height))
    }

    pub fn flush(&self) {
        unsafe { self.context.Flush() };
    }

    /// One row of `captured` (BGRA, texture width): the tooltip marker check.
    pub fn read_row(&self, y: u32) -> std::result::Result<Vec<u8>, Error> {
        if y >= self.size.1 {
            return Err(Error::Invalid("row is outside the texture"));
        }
        let region = D3D11_BOX {
            left: 0,
            top: y,
            front: 0,
            right: self.size.0,
            bottom: y + 1,
            back: 1,
        };
        let mut out = vec![0u8; self.size.0 as usize * 4];
        unsafe {
            self.context.CopySubresourceRegion(
                &self.row,
                0,
                0,
                0,
                0,
                &self.captured,
                0,
                Some(&region),
            );
            let mut mapped = D3D11_MAPPED_SUBRESOURCE::default();
            self.context
                .Map(&self.row, 0, D3D11_MAP_READ, 0, Some(&mut mapped))?;
            std::ptr::copy_nonoverlapping(mapped.pData as *const u8, out.as_mut_ptr(), out.len());
            self.context.Unmap(&self.row, 0);
        }
        Ok(out)
    }

    /// The alpha mask (one byte per pixel) for the image area; also sets the render size.
    pub fn set_mask(
        &mut self,
        data: &[u8],
        width: u32,
        height: u32,
    ) -> std::result::Result<(), Error> {
        if width == 0 || height == 0 || width > self.size.0 || height > self.size.1 {
            return Err(Error::Invalid("mask size must be within the texture"));
        }
        if data.len() as u64 != width as u64 * height as u64 {
            return Err(Error::Invalid("mask must be width * height bytes"));
        }
        if let Some(mask) = self.mask.as_ref().filter(|m| m.size == (width, height)) {
            unsafe {
                self.context.UpdateSubresource(
                    &mask.texture,
                    0,
                    None,
                    data.as_ptr().cast(),
                    width,
                    0,
                )
            };
            return Ok(());
        }
        let init = D3D11_SUBRESOURCE_DATA {
            pSysMem: data.as_ptr().cast(),
            SysMemPitch: width,
            SysMemSlicePitch: 0,
        };
        let (mut texture, mut view) = (None, None);
        unsafe {
            let desc = texture_desc(
                (width, height),
                DXGI_FORMAT_R8_UNORM,
                D3D11_BIND_SHADER_RESOURCE.0 as u32,
            );
            self.device
                .CreateTexture2D(&desc, Some(&init), Some(&mut texture))?;
            self.device.CreateShaderResourceView(
                texture.as_ref().unwrap(),
                None,
                Some(&mut view),
            )?;
        }
        self.mask = Some(Mask {
            texture: texture.unwrap(),
            view: view.unwrap(),
            size: (width, height),
        });
        Ok(())
    }

    /// Compose `captured` x mask into `out` over the mask's area. intro: 0 idle, 1 pending, 2 playing.
    pub fn render(
        &self,
        intro: u32,
        launcher: (i32, i32, i32, i32),
    ) -> std::result::Result<(), Error> {
        let mask = self
            .mask
            .as_ref()
            .ok_or(Error::Invalid("set_mask must be called before render"))?;
        if intro > 2 {
            return Err(Error::Invalid("intro must be 0, 1 or 2"));
        }
        let params = Params {
            intro,
            pad: [0; 3],
            rect: [launcher.0, launcher.1, launcher.2, launcher.3],
        };
        let viewport = D3D11_VIEWPORT {
            TopLeftX: 0.0,
            TopLeftY: 0.0,
            Width: mask.size.0 as f32,
            Height: mask.size.1 as f32,
            MinDepth: 0.0,
            MaxDepth: 1.0,
        };
        let c = &self.context;
        unsafe {
            c.UpdateSubresource(
                &self.params,
                0,
                None,
                (&params as *const Params).cast(),
                0,
                0,
            );
            // SteamVR's client uses this immediate context when we submit, so set every
            // piece of state this pass depends on each time instead of caching it.
            c.ClearState();
            c.IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
            c.VSSetShader(&self.vs, None);
            c.PSSetShader(&self.ps, None);
            c.PSSetShaderResources(
                0,
                Some(&[Some(self.captured_view.clone()), Some(mask.view.clone())]),
            );
            c.PSSetConstantBuffers(0, Some(&[Some(self.params.clone())]));
            c.RSSetViewports(Some(&[viewport]));
            c.OMSetRenderTargets(Some(&[Some(self.out_target.clone())]), None);
            c.Draw(3, 0);
            c.OMSetRenderTargets(None, None);
            c.PSSetShaderResources(0, Some(&[None, None]));
            c.Flush();
        }
        Ok(())
    }

    /// Tests only: `out` as tightly packed BGRA rows.
    pub fn read_back(&self) -> Result<Vec<u8>> {
        let (width, height) = self.size;
        let mut staging = None;
        unsafe {
            self.device
                .CreateTexture2D(&staging_desc(self.size), None, Some(&mut staging))?
        };
        let staging = staging.expect("CreateTexture2D returned no staging texture");
        let row = width as usize * 4;
        let mut out = vec![0u8; row * height as usize];
        unsafe {
            self.context.CopyResource(&staging, &self.out);
            let mut mapped = D3D11_MAPPED_SUBRESOURCE::default();
            self.context
                .Map(&staging, 0, D3D11_MAP_READ, 0, Some(&mut mapped))?;
            for y in 0..height as usize {
                let src = (mapped.pData as *const u8).add(y * mapped.RowPitch as usize);
                std::ptr::copy_nonoverlapping(src, out.as_mut_ptr().add(y * row), row);
            }
            self.context.Unmap(&staging, 0);
        }
        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::copy_box;

    #[test]
    fn copy_box_clips_to_frame_and_owned_texture() {
        let b = copy_box((8, 31, 1698, 911), (1706, 919), (2128, 1136)).unwrap();
        assert_eq!((b.left, b.top, b.right, b.bottom), (8, 31, 1698, 911));
        let b = copy_box((8, 31, 5000, 5000), (1706, 919), (1000, 500)).unwrap();
        assert_eq!((b.right, b.bottom), (1008, 531));
        assert!(copy_box((10, 10, 10, 20), (100, 100), (100, 100)).is_none());
        assert!(copy_box((200, 0, 300, 10), (100, 100), (100, 100)).is_none());
    }
}
