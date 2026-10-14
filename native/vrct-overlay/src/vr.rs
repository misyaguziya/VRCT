//! The OpenVR calls the overlay makes while connected, as traits: SteamVR's (vrct_openvr) in the
//! app, a made-up SteamVR in the tests (tests.rs).
use vrct_openvr::{ComponentState, ControllerModeState, ControllerState, Error, Event, HmdMatrix34, IntersectionParams,
                  IntersectionResults, Texture, TextureBounds, TrackedDevicePose};

pub(crate) trait VrSystem {
    fn device_to_absolute_tracking_pose(&self, origin: i32, predicted_seconds: f32) -> Vec<TrackedDevicePose>;
    fn tracked_device_index_for_controller_role(&self, role: i32) -> u32;
    fn controller_state(&self, index: u32) -> Option<ControllerState>;
    fn poll_next_event(&self) -> Option<Event>;
    fn string_tracked_device_property(&self, index: u32, property: u32) -> String;
    fn tracked_device_activity_level(&self, index: u32) -> i32;
    fn is_tracked_device_connected(&self, index: u32) -> bool;
    fn dxgi_output_info(&self) -> i32;
}

pub(crate) trait VrOverlay {
    fn create_overlay(&self, key: &str, name: &str) -> Result<u64, Error>;
    fn destroy_overlay(&self, handle: u64) -> Result<(), Error>;
    fn show_overlay(&self, handle: u64) -> Result<(), Error>;
    fn hide_overlay(&self, handle: u64) -> Result<(), Error>;
    fn clear_overlay_texture(&self, handle: u64) -> Result<(), Error>;
    fn set_overlay_texture(&self, handle: u64, texture: &Texture) -> Result<(), Error>;
    fn set_overlay_width_in_meters(&self, handle: u64, meters: f32) -> Result<(), Error>;
    fn set_overlay_alpha(&self, handle: u64, alpha: f32) -> Result<(), Error>;
    fn set_overlay_color(&self, handle: u64, red: f32, green: f32, blue: f32) -> Result<(), Error>;
    fn set_overlay_sort_order(&self, handle: u64, order: u32) -> Result<(), Error>;
    fn set_overlay_transform_absolute(&self, handle: u64, origin: i32, transform: &HmdMatrix34) -> Result<(), Error>;
    fn set_overlay_transform_tracked_device_relative(&self, handle: u64, device: u32, transform: &HmdMatrix34) -> Result<(), Error>;
    fn set_overlay_texture_bounds(&self, handle: u64, bounds: &TextureBounds) -> Result<(), Error>;
    fn compute_overlay_intersection(&self, handle: u64, params: &IntersectionParams) -> Option<IntersectionResults>;
}

pub(crate) trait VrRenderModels {
    fn component_state(&self, model: &str, component: &str, state: &ControllerState, mode: &ControllerModeState)
                       -> Option<ComponentState>;
}

impl VrSystem for vrct_openvr::System<'_> {
    fn device_to_absolute_tracking_pose(&self, origin: i32, predicted_seconds: f32) -> Vec<TrackedDevicePose> {
        self.device_to_absolute_tracking_pose(origin, predicted_seconds)
    }
    fn tracked_device_index_for_controller_role(&self, role: i32) -> u32 {
        self.tracked_device_index_for_controller_role(role)
    }
    fn controller_state(&self, index: u32) -> Option<ControllerState> {
        self.controller_state(index)
    }
    fn poll_next_event(&self) -> Option<Event> {
        self.poll_next_event()
    }
    fn string_tracked_device_property(&self, index: u32, property: u32) -> String {
        self.string_tracked_device_property(index, property)
    }
    fn tracked_device_activity_level(&self, index: u32) -> i32 {
        self.tracked_device_activity_level(index)
    }
    fn is_tracked_device_connected(&self, index: u32) -> bool {
        self.is_tracked_device_connected(index)
    }
    fn dxgi_output_info(&self) -> i32 {
        self.dxgi_output_info()
    }
}

impl VrOverlay for vrct_openvr::Overlay<'_> {
    fn create_overlay(&self, key: &str, name: &str) -> Result<u64, Error> {
        self.create_overlay(key, name)
    }
    fn destroy_overlay(&self, handle: u64) -> Result<(), Error> {
        self.destroy_overlay(handle)
    }
    fn show_overlay(&self, handle: u64) -> Result<(), Error> {
        self.show_overlay(handle)
    }
    fn hide_overlay(&self, handle: u64) -> Result<(), Error> {
        self.hide_overlay(handle)
    }
    fn clear_overlay_texture(&self, handle: u64) -> Result<(), Error> {
        self.clear_overlay_texture(handle)
    }
    fn set_overlay_texture(&self, handle: u64, texture: &Texture) -> Result<(), Error> {
        self.set_overlay_texture(handle, texture)
    }
    fn set_overlay_width_in_meters(&self, handle: u64, meters: f32) -> Result<(), Error> {
        self.set_overlay_width_in_meters(handle, meters)
    }
    fn set_overlay_alpha(&self, handle: u64, alpha: f32) -> Result<(), Error> {
        self.set_overlay_alpha(handle, alpha)
    }
    fn set_overlay_color(&self, handle: u64, red: f32, green: f32, blue: f32) -> Result<(), Error> {
        self.set_overlay_color(handle, red, green, blue)
    }
    fn set_overlay_sort_order(&self, handle: u64, order: u32) -> Result<(), Error> {
        self.set_overlay_sort_order(handle, order)
    }
    fn set_overlay_transform_absolute(&self, handle: u64, origin: i32, transform: &HmdMatrix34) -> Result<(), Error> {
        self.set_overlay_transform_absolute(handle, origin, transform)
    }
    fn set_overlay_transform_tracked_device_relative(&self, handle: u64, device: u32, transform: &HmdMatrix34) -> Result<(), Error> {
        self.set_overlay_transform_tracked_device_relative(handle, device, transform)
    }
    fn set_overlay_texture_bounds(&self, handle: u64, bounds: &TextureBounds) -> Result<(), Error> {
        self.set_overlay_texture_bounds(handle, bounds)
    }
    fn compute_overlay_intersection(&self, handle: u64, params: &IntersectionParams) -> Option<IntersectionResults> {
        self.compute_overlay_intersection(handle, params)
    }
}

impl VrRenderModels for vrct_openvr::RenderModels<'_> {
    fn component_state(&self, model: &str, component: &str, state: &ControllerState, mode: &ControllerModeState)
                       -> Option<ComponentState> {
        self.component_state(model, component, state, mode)
    }
}
