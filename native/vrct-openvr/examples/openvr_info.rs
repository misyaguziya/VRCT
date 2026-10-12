//! Joins SteamVR as a background app (no window, nothing shown) and prints what VRCT reads:
//! the headset's activity, the controllers, the running SteamVR app. Without SteamVR running it
//! only prints the init error.
//!     cargo run -p vrct-openvr --example openvr_info
use vrct_openvr::*;

fn main() {
    let session = match acquire(ApplicationType::Background) {
        Ok(s) => s,
        Err(e) => return println!("init: {e}"),
    };
    let system = session.system().unwrap();
    println!("hmd activity {}", system.tracked_device_activity_level(TRACKED_DEVICE_INDEX_HMD));
    for (role, name) in [(CONTROLLER_ROLE_LEFT_HAND, "left"), (CONTROLLER_ROLE_RIGHT_HAND, "right")] {
        let index = system.tracked_device_index_for_controller_role(role);
        println!("{name} hand: index {index} model {:?}", system.string_tracked_device_property(index, PROP_RENDER_MODEL_NAME_STRING));
    }
    let poses = system.device_to_absolute_tracking_pose(TRACKING_UNIVERSE_STANDING, 0.0);
    println!("hmd pose valid {} {:?}", poses[0].pose_is_valid, poses[0].device_to_absolute_tracking[0]);
    let apps = session.applications().unwrap();
    for i in 0..apps.application_count() {
        let key = apps.application_key_by_index(i);
        if key.starts_with("steam.app") {
            println!("app {key} {:?}", apps.application_property_string(&key, APPLICATION_PROPERTY_NAME_STRING));
        }
    }
    println!("dxgi adapter {}", system.dxgi_output_info());
}
