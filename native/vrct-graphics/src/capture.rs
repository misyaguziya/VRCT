//! Windows.Graphics.Capture into a texture this module owns, on a chosen DXGI
//! adapter (SteamVR's). No CPU copy on the per-frame path; `read_back` exists
//! only to verify pixels without SteamVR. Everything runs on the caller's
//! thread: the frame pool is free-threaded and polled, never called back.
use windows::{
    core::{Interface, Result},
    Graphics::{
        Capture::{Direct3D11CaptureFramePool, GraphicsCaptureItem, GraphicsCaptureSession},
        DirectX::{Direct3D11::IDirect3DDevice, DirectXPixelFormat},
        SizeInt32,
    },
    Win32::{
        Foundation::{HMODULE, HWND},
        Graphics::{
            Direct3D::D3D_DRIVER_TYPE_UNKNOWN,
            Direct3D11::{
                D3D11CreateDevice, ID3D11Device, ID3D11DeviceContext, ID3D11Texture2D,
                D3D11_BIND_RENDER_TARGET, D3D11_BIND_SHADER_RESOURCE, D3D11_BOX,
                D3D11_CPU_ACCESS_READ, D3D11_CREATE_DEVICE_BGRA_SUPPORT, D3D11_MAPPED_SUBRESOURCE,
                D3D11_MAP_READ, D3D11_RESOURCE_MISC_SHARED, D3D11_SDK_VERSION,
                D3D11_SUBRESOURCE_DATA, D3D11_TEXTURE2D_DESC, D3D11_USAGE_DEFAULT,
                D3D11_USAGE_STAGING,
            },
            Dxgi::{
                Common::{DXGI_FORMAT_B8G8R8A8_UNORM, DXGI_SAMPLE_DESC},
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

/// Copy box for the client rectangle inside a captured frame, clipped to both textures.
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
    pub content: (u32, u32),
    pub copied: (u32, u32),
    pub system_time_100ns: i64,
}

pub struct Capture {
    device: ID3D11Device,
    context: ID3D11DeviceContext,
    winrt_device: IDirect3DDevice,
    pool: Direct3D11CaptureFramePool,
    session: GraphicsCaptureSession,
    owned: ID3D11Texture2D,
    owned_size: (u32, u32),
    pool_size: SizeInt32,
    frame_id: u64,
}

impl Capture {
    pub fn new(
        hwnd: isize,
        adapter_index: u32,
        width: u32,
        height: u32,
        shared: bool,
    ) -> Result<Self> {
        // An apartment set up by someone else (RPC_E_CHANGED_MODE) is fine for a free-threaded pool.
        let _ = unsafe { RoInitialize(RO_INIT_MULTITHREADED) };
        let factory: IDXGIFactory1 = unsafe { CreateDXGIFactory1()? };
        let adapter = unsafe { factory.EnumAdapters1(adapter_index)? };
        let mut device = None;
        let mut context = None;
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

        let interop = windows::core::factory::<GraphicsCaptureItem, IGraphicsCaptureItemInterop>()?;
        let item: GraphicsCaptureItem = unsafe { interop.CreateForWindow(HWND(hwnd as _))? };
        let pool_size = item.Size()?;
        let pool = Direct3D11CaptureFramePool::CreateFreeThreaded(
            &winrt_device,
            FORMAT,
            BUFFERS,
            pool_size,
        )?;
        let session = pool.CreateCaptureSession(&item)?;
        session.SetIsCursorCaptureEnabled(false)?;
        // Not available before Windows 10 2104 / 11: then the yellow border stays.
        let _ = session.SetIsBorderRequired(false);

        let desc = D3D11_TEXTURE2D_DESC {
            Width: width,
            Height: height,
            MipLevels: 1,
            ArraySize: 1,
            Format: DXGI_FORMAT_B8G8R8A8_UNORM,
            SampleDesc: DXGI_SAMPLE_DESC {
                Count: 1,
                Quality: 0,
            },
            Usage: D3D11_USAGE_DEFAULT,
            BindFlags: (D3D11_BIND_SHADER_RESOURCE.0 | D3D11_BIND_RENDER_TARGET.0) as u32,
            CPUAccessFlags: 0,
            MiscFlags: if shared {
                D3D11_RESOURCE_MISC_SHARED.0 as u32
            } else {
                0
            },
        };
        // Start fully transparent so a region never shows stale GPU memory.
        let zeros = vec![0u8; width as usize * height as usize * 4];
        let init = D3D11_SUBRESOURCE_DATA {
            pSysMem: zeros.as_ptr().cast(),
            SysMemPitch: width * 4,
            SysMemSlicePitch: 0,
        };
        let mut owned = None;
        unsafe { device.CreateTexture2D(&desc, Some(&init), Some(&mut owned))? };
        let owned = owned.expect("CreateTexture2D returned no texture");
        session.StartCapture()?;
        Ok(Self {
            device,
            context,
            winrt_device,
            pool,
            session,
            owned,
            owned_size: (width, height),
            pool_size,
            frame_id: 0,
        })
    }

    pub fn texture_ptr(&self) -> usize {
        self.owned.as_raw() as usize
    }

    pub fn size(&self) -> (u32, u32) {
        self.owned_size
    }

    /// Copies the newest frame (if any arrived) into the owned texture. Never waits.
    pub fn poll(&mut self, client: (u32, u32, u32, u32)) -> Result<Option<Polled>> {
        let mut latest = None;
        // Drain to the newest frame; older ones go straight back to the pool.
        while let Ok(frame) = self.pool.TryGetNextFrame() {
            if let Some(old) = latest.replace(frame) {
                old.Close()?;
            }
        }
        let Some(frame) = latest else { return Ok(None) };
        let content = frame.ContentSize()?;
        let surface = frame.Surface()?;
        let access: IDirect3DDxgiInterfaceAccess = surface.cast()?;
        let texture: ID3D11Texture2D = unsafe { access.GetInterface()? };
        let mut desc = D3D11_TEXTURE2D_DESC::default();
        unsafe { texture.GetDesc(&mut desc) };
        let copied = match copy_box(client, (desc.Width, desc.Height), self.owned_size) {
            Some(region) => {
                unsafe {
                    self.context.CopySubresourceRegion(
                        &self.owned,
                        0,
                        0,
                        0,
                        0,
                        &texture,
                        0,
                        Some(&region),
                    );
                    self.context.Flush();
                }
                (region.right - region.left, region.bottom - region.top)
            }
            None => (0, 0),
        };
        let system_time_100ns = frame.SystemRelativeTime()?.Duration;
        frame.Close()?;
        if content.Width != self.pool_size.Width || content.Height != self.pool_size.Height {
            // The window was resized: later frames come at the new size.
            self.pool
                .Recreate(&self.winrt_device, FORMAT, BUFFERS, content)?;
            self.pool_size = content;
        }
        self.frame_id += 1;
        Ok(Some(Polled {
            frame_id: self.frame_id,
            content: (content.Width as u32, content.Height as u32),
            copied,
            system_time_100ns,
        }))
    }

    /// PoC check only: the owned texture as tightly packed BGRA rows.
    pub fn read_back(&self) -> Result<Vec<u8>> {
        let (width, height) = self.owned_size;
        let desc = D3D11_TEXTURE2D_DESC {
            Width: width,
            Height: height,
            MipLevels: 1,
            ArraySize: 1,
            Format: DXGI_FORMAT_B8G8R8A8_UNORM,
            SampleDesc: DXGI_SAMPLE_DESC {
                Count: 1,
                Quality: 0,
            },
            Usage: D3D11_USAGE_STAGING,
            BindFlags: 0,
            CPUAccessFlags: D3D11_CPU_ACCESS_READ.0 as u32,
            MiscFlags: 0,
        };
        let mut staging = None;
        unsafe {
            self.device
                .CreateTexture2D(&desc, None, Some(&mut staging))?
        };
        let staging = staging.expect("CreateTexture2D returned no staging texture");
        let row = width as usize * 4;
        let mut out = vec![0u8; row * height as usize];
        unsafe {
            self.context.CopyResource(&staging, &self.owned);
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

    pub fn close(&self) {
        let _ = self.session.Close();
        let _ = self.pool.Close();
    }
}

impl Drop for Capture {
    fn drop(&mut self) {
        self.close();
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
