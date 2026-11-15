//! The OpenVR calls the overlay makes while connected, as traits: SteamVR's (vrct_openvr) in the
//! app, a made-up SteamVR in the tests (tests.rs).
use vrct_openvr::{ComponentState, ControllerModeState, ControllerState, Error, Event, HmdMatrix34, IntersectionParams,
                  IntersectionResults, Texture, TextureBounds, TrackedDevicePose};

pub(crate) trait VrSystem {
    fn device_to_absolute_tracking_pose(&self, origin: i32, predicted_seconds: f32) -> Vec<TrackedDevicePose>;
    fn tracked_device_index_for_controller_role(&self, role: i32) -> u32;
    fn controller_state(&self, index: u32) -> Option<ControllerState>;
    /// Once a frame, before the controller states: the hands (device indices) pointing at VRCT,
    /// held from the game (input.rs)
    fn update_input(&self, _pointing: &[u32]) -> Result<(), Error> { Ok(()) }
    fn is_input_available(&self) -> bool { true }
    fn invalidate_input(&self) {}
    fn trigger_haptic_pulse(&self, index: u32, duration_us: u16);
    fn poll_next_event(&self) -> Option<Event>;
    fn string_tracked_device_property(&self, index: u32, property: u32) -> String;
    fn tracked_device_activity_level(&self, index: u32) -> i32;
    fn is_tracked_device_connected(&self, index: u32) -> bool;
    fn dxgi_output_info(&self) -> i32;
}

pub(crate) trait VrOverlay {
    fn is_dashboard_visible(&self) -> bool { false }
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

/// SteamVR's system, its hands read through SteamVR Input (the legacy controller state when the
/// actions could not be set up)
pub(crate) struct SteamVrSystem<'s> {
    pub system: vrct_openvr::System<'s>,
    pub actions: Option<crate::input::Actions<vrct_openvr::Input<'s>>>,
}

impl SteamVrSystem<'_> {
    /// 0: the left hand, 1: the right hand
    fn hand_of(&self, index: u32) -> Option<usize> {
        [vrct_openvr::CONTROLLER_ROLE_LEFT_HAND, vrct_openvr::CONTROLLER_ROLE_RIGHT_HAND]
            .iter().position(|&role| index != vrct_openvr::TRACKED_DEVICE_INDEX_INVALID && self.system.tracked_device_index_for_controller_role(role) == index)
    }
}

impl VrSystem for SteamVrSystem<'_> {
    fn device_to_absolute_tracking_pose(&self, origin: i32, predicted_seconds: f32) -> Vec<TrackedDevicePose> {
        self.system.device_to_absolute_tracking_pose(origin, predicted_seconds)
    }
    fn tracked_device_index_for_controller_role(&self, role: i32) -> u32 {
        self.system.tracked_device_index_for_controller_role(role)
    }
    fn controller_state(&self, index: u32) -> Option<ControllerState> {
        match &self.actions {
            Some(actions) => self.hand_of(index).and_then(|hand| actions.state(hand)),
            None => self.system.controller_state(index),
        }
    }
    fn update_input(&self, pointing: &[u32]) -> Result<(), Error> {
        if let Some(actions) = &self.actions {
            let mut wanted = [false; 2];
            for &index in pointing {
                if let Some(hand) = self.hand_of(index) {
                    wanted[hand] = true;
                }
            }
            actions.update(wanted)?;
        }
        Ok(())
    }
    fn is_input_available(&self) -> bool { self.system.is_input_available() }
    fn invalidate_input(&self) {
        if let Some(actions) = &self.actions { actions.invalidate(); }
    }
    fn trigger_haptic_pulse(&self, index: u32, duration_us: u16) {
        self.system.trigger_haptic_pulse(index, 0, duration_us)
    }
    fn poll_next_event(&self) -> Option<Event> {
        self.system.poll_next_event()
    }
    fn string_tracked_device_property(&self, index: u32, property: u32) -> String {
        self.system.string_tracked_device_property(index, property)
    }
    fn tracked_device_activity_level(&self, index: u32) -> i32 {
        self.system.tracked_device_activity_level(index)
    }
    fn is_tracked_device_connected(&self, index: u32) -> bool {
        self.system.is_tracked_device_connected(index)
    }
    fn dxgi_output_info(&self) -> i32 {
        self.system.dxgi_output_info()
    }
}

impl VrOverlay for vrct_openvr::Overlay<'_> {
    fn is_dashboard_visible(&self) -> bool { self.is_dashboard_visible() }
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
