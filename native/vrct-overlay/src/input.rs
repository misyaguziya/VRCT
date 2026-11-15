//! The hands read through SteamVR Input, and held from VRChat while they point at VRCT.
//!
//! While a hand points at one of the windows (or grabs one), its trigger, grip and A/B/X/Y reach VRCT
//! only: an action set at IVRInput's overlay-global priority, restricted to that hand (SteamVR's
//! "Enable global input from overlays" must be on). Only what a set holds is held, and the game
//! keeps the last value it got when the hold began, so sticks are never held (a stick pushed then
//! would keep VRChat walking), and a hold begins only with the trigger, grip and buttons up.
//! What is held so reaches the holding process only, and a process with actions reads no
//! legacy controller state (all 0): every button the overlay uses is an action here, handed to the
//! rest as the ControllerState it read before.
use vrct_openvr::{input, ActiveActionSet, ControllerState, Input};
use serde_json::{json, Value};
use std::cell::Cell;
use std::path::Path;

/// The trigger let go (a hold begins only below this)
const TRIGGER_REST: f32 = 0.1;

const MAIN: &str = "/actions/main";
const HOLD: &str = "/actions/hold";

/// Each controller's inputs: (type, stick and its mode, grip mode, [the upper / lower face button]
/// of the left and right hand). The upper one is the application menu (the shortcut's).
struct Controller {
    kind: &'static str,
    stick: (&'static str, &'static str),
    grip_mode: &'static str,
    /// [left, right]: (upper, lower) face button, lower None when there is none
    buttons: [(&'static str, Option<&'static str>); 2],
}

const CONTROLLERS: [Controller; 6] = [
    Controller { kind: "oculus_touch", stick: ("joystick", "joystick"), grip_mode: "trigger", buttons: [("y", Some("x")), ("b", Some("a"))] },
    Controller { kind: "knuckles", stick: ("thumbstick", "joystick"), grip_mode: "grab", buttons: [("b", Some("a")), ("b", Some("a"))] },
    Controller { kind: "vive_controller", stick: ("trackpad", "trackpad"), grip_mode: "button",
                 buttons: [("application_menu", None), ("application_menu", None)] },
    Controller { kind: "holographic_controller", stick: ("joystick", "joystick"), grip_mode: "button", buttons: [("menu", None), ("menu", None)] },
    Controller { kind: "hpmotioncontroller", stick: ("joystick", "joystick"), grip_mode: "trigger", buttons: [("y", Some("x")), ("b", Some("a"))] },
    Controller { kind: "vive_cosmos_controller", stick: ("joystick", "joystick"), grip_mode: "button", buttons: [("y", Some("x")), ("b", Some("a"))] },
];

fn manifest() -> Value {
    let action = |name: &str, kind: &str| json!({"name": name, "type": kind, "requirement": "optional"});
    json!({
        "default_bindings": CONTROLLERS.iter()
            .map(|c| json!({"controller_type": c.kind, "binding_url": format!("bindings_{}.json", c.kind)})).collect::<Vec<_>>(),
        "actions": [
            action("/actions/main/in/trigger", "vector1"), action("/actions/main/in/trigger_click", "boolean"),
            action("/actions/main/in/grip", "boolean"), action("/actions/main/in/stick", "vector2"),
            action("/actions/main/in/stick_click", "boolean"), action("/actions/main/in/upper", "boolean"),
            action("/actions/main/in/lower", "boolean"),
            action("/actions/hold/in/trigger", "vector1"), action("/actions/hold/in/trigger_click", "boolean"),
            action("/actions/hold/in/grip", "boolean"),
            action("/actions/hold/in/upper", "boolean"), action("/actions/hold/in/lower", "boolean"),
        ],
        "action_sets": [{"name": MAIN, "usage": "leftright"}, {"name": HOLD, "usage": "leftright"}],
        "localization": [{
            "language_tag": "en_US",
            "/actions/main": "VRCT", "/actions/hold": "VRCT: held from the game while pointing at VRCT",
            "/actions/main/in/trigger": "Trigger", "/actions/main/in/trigger_click": "Press keys",
            "/actions/main/in/grip": "Grab windows", "/actions/main/in/stick": "Scroll / move a window nearer",
            "/actions/main/in/stick_click": "Shortcut (stick)", "/actions/main/in/upper": "Shortcut (menu)",
            "/actions/main/in/lower": "Lower button",
            "/actions/hold/in/trigger": "Trigger", "/actions/hold/in/trigger_click": "Press keys",
            "/actions/hold/in/grip": "Grab windows",
            "/actions/hold/in/upper": "Upper button", "/actions/hold/in/lower": "Lower button",
        }],
    })
}

fn bindings(c: &Controller) -> Value {
    let mut main = vec![];
    let mut hold = vec![];
    for (hand, (upper, lower)) in ["left", "right"].into_iter().zip(c.buttons) {
        let path = |input: &str| format!("/user/hand/{hand}/input/{input}");
        let out = |set: &str, name: &str| json!({"output": format!("{set}/in/{name}")});
        let button = |set: &str, input: &str, name: &str| json!({"path": path(input), "mode": "button", "inputs": {"click": out(set, name)}});
        main.push(json!({"path": path("trigger"), "mode": "trigger", "inputs": {"pull": out(MAIN, "trigger"), "click": out(MAIN, "trigger_click")}}));
        for (set, sources) in [(MAIN, &mut main), (HOLD, &mut hold)] {
            let grip = if c.grip_mode == "grab" { json!({"grab": out(set, "grip")}) } else { json!({"click": out(set, "grip")}) };
            sources.push(json!({"path": path("grip"), "mode": c.grip_mode, "inputs": grip}));
        }
        main.push(json!({"path": path(c.stick.0), "mode": c.stick.1, "inputs": {"position": out(MAIN, "stick"), "click": out(MAIN, "stick_click")}}));
        main.push(button(MAIN, upper, "upper"));
        hold.push(json!({"path": path("trigger"), "mode": "trigger", "inputs": {"pull": out(HOLD, "trigger"), "click": out(HOLD, "trigger_click")}}));
        hold.push(button(HOLD, upper, "upper"));
        if let Some(lower) = lower {
            main.push(button(MAIN, lower, "lower"));
            hold.push(button(HOLD, lower, "lower"));
        }
    }
    json!({"controller_type": c.kind, "bindings": {MAIN: {"sources": main}, HOLD: {"sources": hold}}})
}

/// The actions of one set
struct Set {
    handle: u64,
    trigger: u64,
    trigger_click: u64,
    grip: u64,
    upper: u64,
    lower: u64,
}

#[derive(Clone, Copy)]
struct Snapshot {
    state: ControllerState,
    lower: Option<bool>,
    available: u8,
}

impl Snapshot {
    fn hold_neutral(self) -> bool {
        let mask = (1 << vrct_openvr::BUTTON_STEAMVR_TRIGGER) | (1 << vrct_openvr::BUTTON_APPLICATION_MENU)
            | (1 << vrct_openvr::BUTTON_GRIP);
        self.state.axis[1][0] < TRIGGER_REST && self.state.button_pressed & mask == 0 && self.lower != Some(true)
    }
}

/// Back from an interruption once nothing that presses is held (a held grip grabs nothing, the
/// stick and a finger resting on the trigger press nothing: walking or holding something in the
/// game does not keep the hand out)
fn ready_after(ready: bool, snapshot: Option<Snapshot>) -> bool {
    snapshot.is_some_and(|s| ready || (s.state.button_pressed & !(1 << vrct_openvr::BUTTON_GRIP) == 0 && s.lower != Some(true)))
}

/// The per-frame calls, kept separate from manifest setup so recovery can be tested without VR.
pub(crate) trait ActionInput {
    fn digital_action_data(&self, action: u64, device: u64) -> Result<vrct_openvr::DigitalActionData, vrct_openvr::Error>;
    fn analog_action_data(&self, action: u64, device: u64) -> Result<vrct_openvr::AnalogActionData, vrct_openvr::Error>;
    fn update_action_state(&self, sets: &mut [ActiveActionSet]) -> Result<(), vrct_openvr::Error>;
}

impl ActionInput for Input<'_> {
    fn digital_action_data(&self, action: u64, device: u64) -> Result<vrct_openvr::DigitalActionData, vrct_openvr::Error> {
        Input::digital_action_data(self, action, device)
    }

    fn analog_action_data(&self, action: u64, device: u64) -> Result<vrct_openvr::AnalogActionData, vrct_openvr::Error> {
        Input::analog_action_data(self, action, device)
    }

    fn update_action_state(&self, sets: &mut [ActiveActionSet]) -> Result<(), vrct_openvr::Error> {
        Input::update_action_state(self, sets)
    }
}

pub(crate) struct Actions<I> {
    input: I,
    main: Set,
    hold: Set,
    stick: u64,
    stick_click: u64,
    /// the hands' input sources: left, right
    hands: [u64; 2],
    held: Cell<[bool; 2]>,
    snapshots: Cell<[Option<Snapshot>; 2]>,
    ready: Cell<[bool; 2]>,
}

impl<'s> Actions<Input<'s>> {
    /// The manifest and the default bindings written to `dir`, and given to SteamVR
    pub fn new(input: Input<'s>, dir: &Path) -> anyhow::Result<Self> {
        std::fs::create_dir_all(dir)?;
        std::fs::write(dir.join("actions.json"), serde_json::to_string_pretty(&manifest())?)?;
        for c in &CONTROLLERS {
            std::fs::write(dir.join(format!("bindings_{}.json", c.kind)), serde_json::to_string_pretty(&bindings(c))?)?;
        }
        input.set_action_manifest_path(&dir.join("actions.json"))?;
        let set = |name: &str| -> anyhow::Result<Set> {
            let action = |a: &str| input.action_handle(&format!("{name}/in/{a}"));
            Ok(Set { handle: input.action_set_handle(name)?, trigger: action("trigger")?, trigger_click: action("trigger_click")?,
                     grip: action("grip")?, upper: action("upper")?, lower: action("lower")? })
        };
        let (main, hold) = (set(MAIN)?, set(HOLD)?);
        let action = |a: &str| input.action_handle(&format!("{MAIN}/in/{a}"));
        let (stick, stick_click) = (action("stick")?, action("stick_click")?);
        let hands = [input.input_source_handle("/user/hand/left")?, input.input_source_handle("/user/hand/right")?];
        Ok(Self { input, main, hold, stick, stick_click, hands, held: Cell::new([false; 2]), snapshots: Cell::new([None; 2]), ready: Cell::new([false; 2]) })
    }
}

impl<I: ActionInput> Actions<I> {
    /// Inactive is retained as None; API errors invalidate the whole hand snapshot.
    fn digital(&self, action: u64, hand: usize) -> Result<Option<bool>, vrct_openvr::Error> {
        self.input.digital_action_data(action, self.hands[hand]).map(|d| d.active.then_some(d.state))
    }

    fn analog(&self, action: u64, hand: usize) -> Result<Option<(f32, f32)>, vrct_openvr::Error> {
        self.input.analog_action_data(action, self.hands[hand])
            .map(|d| (d.active && d.x.is_finite() && d.y.is_finite()).then_some((d.x, d.y)))
    }

    fn read(&self, hand: usize, held: bool) -> Option<Snapshot> {
        let set = if held { &self.hold } else { &self.main };
        let trigger = self.analog(set.trigger, hand).ok()??.0;
        let click = self.digital(set.trigger_click, hand).ok()??;
        let upper = self.digital(set.upper, hand).ok()?;
        // Vive/WMR have no lower face button. Keep its availability instead of inventing one.
        let lower = self.digital(set.lower, hand).ok()?;
        let grip = self.digital(set.grip, hand).ok()?;
        // Existing custom bindings may not have hold/grip yet. Preserve grabbing via MAIN
        // in that case (without promising grip suppression). Errors must still suspend input.
        let grip = if held && grip.is_none() { self.digital(self.main.grip, hand).ok()? } else { grip };
        let stick = self.analog(self.stick, hand).ok()?;
        let stick_click = self.digital(self.stick_click, hand).ok()?;
        let available = [upper.is_some(), lower.is_some(), grip.is_some(), stick.is_some(), stick_click.is_some()]
            .iter().enumerate().fold(0, |mask, (i, active)| mask | (u8::from(*active) << i));
        let bit = |on: bool, button: u32| if on { 1u64 << button } else { 0 };
        let mut state = ControllerState {
            button_pressed: bit(click, vrct_openvr::BUTTON_STEAMVR_TRIGGER)
                | bit(grip == Some(true), vrct_openvr::BUTTON_GRIP)
                | bit(upper == Some(true), vrct_openvr::BUTTON_APPLICATION_MENU)
                | bit(stick_click == Some(true), vrct_openvr::BUTTON_AXIS0),
            ..Default::default()
        };
        state.axis[0] = stick.map_or([0.0, 0.0], |(x, y)| [x, y]);
        state.axis[1] = [trigger, 0.0];
        Some(Snapshot { state, lower, available })
    }

    pub fn invalidate(&self) {
        self.snapshots.set([None; 2]);
        self.ready.set([false; 2]);
        self.held.set([false; 2]);
    }

    /// Exactly one runtime update per loop. The current ray selects requested holds;
    /// the preceding valid snapshot is used only for the safe neutral acquisition gate.
    pub fn update(&self, wanted: [bool; 2]) -> Result<(), vrct_openvr::Error> {
        let previous = self.snapshots.get();
        let held = std::array::from_fn(|h| wanted[h] &&
            previous[h].is_some_and(|s| self.held.get()[h] || s.hold_neutral()));
        let mut sets = vec![ActiveActionSet { action_set: self.main.handle, ..Default::default() }];
        for hand in (0..2).filter(|&h| held[h]) {
            sets.push(ActiveActionSet { action_set: self.hold.handle, restricted_to_device: self.hands[hand],
                                        priority: input::OVERLAY_GLOBAL_PRIORITY_MIN + 1, ..Default::default() });
        }
        if let Err(error) = self.input.update_action_state(&mut sets) {
            self.invalidate();
            return Err(error);
        }
        self.held.set(held);
        let snapshots = std::array::from_fn(|h| self.read(h, held[h]));
        self.ready.set(std::array::from_fn(|h| {
            let availability_changed = previous[h].zip(snapshots[h]).is_some_and(|(a, b)| a.available != b.available);
            !availability_changed && ready_after(self.ready.get()[h], snapshots[h])
        }));
        self.snapshots.set(snapshots);
        Ok(())
    }

    pub fn state(&self, hand: usize) -> Option<ControllerState> {
        self.snapshots.get()[hand].filter(|_| self.ready.get()[hand]).map(|s| s.state)
    }

}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;
    use std::collections::HashMap;
    use vrct_openvr::{AnalogActionData, DigitalActionData, Error};

    #[derive(Default)]
    struct FakeInput {
        digital: RefCell<HashMap<(u64, u64), Result<DigitalActionData, Error>>>,
        analog: RefCell<HashMap<(u64, u64), Result<AnalogActionData, Error>>>,
        reads: RefCell<Vec<(u64, u64)>>,
        updates: RefCell<Vec<Vec<ActiveActionSet>>>,
        update_error: Cell<bool>,
    }

    fn input_error() -> Error {
        Error { code: 1, message: "simulated input failure".into() }
    }

    impl ActionInput for FakeInput {
        fn digital_action_data(&self, action: u64, device: u64) -> Result<DigitalActionData, Error> {
            self.reads.borrow_mut().push((action, device));
            self.digital.borrow().get(&(action, device)).expect("unexpected digital action").clone()
        }

        fn analog_action_data(&self, action: u64, device: u64) -> Result<AnalogActionData, Error> {
            self.reads.borrow_mut().push((action, device));
            self.analog.borrow().get(&(action, device)).expect("unexpected analog action").clone()
        }

        fn update_action_state(&self, sets: &mut [ActiveActionSet]) -> Result<(), Error> {
            self.updates.borrow_mut().push(sets.to_vec());
            if self.update_error.get() { Err(input_error()) } else { Ok(()) }
        }
    }

    impl Actions<FakeInput> {
        fn fixture() -> Self {
            let set = |base| Set { handle: base, trigger: base + 1, trigger_click: base + 2,
                                  grip: base + 3, upper: base + 4, lower: base + 5 };
            let actions = Self { input: FakeInput::default(), main: set(10), hold: set(20), stick: 30,
                stick_click: 31, hands: [100, 200], held: Cell::new([false; 2]),
                snapshots: Cell::new([None; 2]), ready: Cell::new([false; 2]) };
            for hand in 0..2 {
                for set in [&actions.main, &actions.hold] {
                    for action in [set.trigger_click, set.grip, set.upper, set.lower] {
                        // Vive and WMR have no lower face button.
                        actions.digital_value(action, hand, action != set.lower, false);
                    }
                    actions.input.analog.borrow_mut().insert((set.trigger, actions.hands[hand]),
                        Ok(AnalogActionData { active: true, ..Default::default() }));
                }
                actions.digital_value(actions.stick_click, hand, true, false);
                actions.input.analog.borrow_mut().insert((actions.stick, actions.hands[hand]),
                    Ok(AnalogActionData { active: true, ..Default::default() }));
            }
            actions
        }

        fn digital_value(&self, action: u64, hand: usize, active: bool, state: bool) {
            self.input.digital.borrow_mut().insert((action, self.hands[hand]),
                Ok(DigitalActionData { active, state, ..Default::default() }));
        }

        fn acquire_both(&self) {
            self.update([true; 2]).unwrap();
            self.update([true; 2]).unwrap();
            assert_eq!(self.held.get(), [true; 2]);
            assert!(self.state(0).is_some() && self.state(1).is_some());
            let updates = self.input.updates.borrow();
            let sets = updates.last().unwrap();
            assert_eq!(sets.len(), 3);
            assert_eq!(sets[0].action_set, self.main.handle);
            assert_eq!(sets[0].priority, 0);
            for hand in 0..2 {
                assert_eq!(sets[hand + 1].action_set, self.hold.handle);
                assert_eq!(sets[hand + 1].restricted_to_device, self.hands[hand]);
                assert!(sets[hand + 1].priority > input::OVERLAY_GLOBAL_PRIORITY_MIN);
            }
        }

        fn pressed(&self, hand: usize, button: u32) -> bool {
            self.state(hand).unwrap().button_pressed & (1 << button) != 0
        }
    }

    #[test]
    fn inactive_hold_grip_falls_back_but_active_release_does_not() {
        let actions = Actions::fixture();
        actions.digital_value(actions.hold.grip, 0, false, false);
        actions.acquire_both();
        actions.digital_value(actions.main.grip, 0, true, true);
        actions.input.reads.borrow_mut().clear();
        actions.update([true; 2]).unwrap();
        assert!(actions.pressed(0, vrct_openvr::BUTTON_GRIP));
        assert!(actions.input.reads.borrow().contains(&(actions.main.grip, actions.hands[0])));

        actions.digital_value(actions.hold.grip, 0, true, false);
        actions.input.reads.borrow_mut().clear();
        actions.update([true; 2]).unwrap();
        assert!(!actions.pressed(0, vrct_openvr::BUTTON_GRIP));
        assert!(!actions.input.reads.borrow().contains(&(actions.main.grip, actions.hands[0])));
    }

    #[test]
    fn grip_errors_suspend_only_the_affected_hand_without_error_fallback() {
        for fallback_error in [false, true] {
            let actions = Actions::fixture();
            actions.acquire_both();
            actions.digital_value(actions.main.grip, 0, true, true);
            actions.digital_value(actions.hold.trigger_click, 1, true, true);
            let failed_action = if fallback_error {
                actions.digital_value(actions.hold.grip, 0, false, false);
                actions.main.grip
            } else { actions.hold.grip };
            actions.input.digital.borrow_mut().insert((failed_action, actions.hands[0]), Err(input_error()));
            actions.input.reads.borrow_mut().clear();
            actions.update([true; 2]).unwrap();
            assert!(actions.state(0).is_none());
            assert!(actions.pressed(1, vrct_openvr::BUTTON_STEAMVR_TRIGGER));
            assert_eq!(actions.input.reads.borrow().contains(&(actions.main.grip, actions.hands[0])), fallback_error);
        }
    }

    #[test]
    fn action_error_recovery_requires_release_before_accepting_a_press() {
        let actions = Actions::fixture();
        actions.acquire_both();
        actions.input.analog.borrow_mut().insert((actions.hold.trigger, actions.hands[0]), Err(input_error()));
        actions.update([true; 2]).unwrap();
        assert!(actions.state(0).is_none());
        actions.input.analog.borrow_mut().insert((actions.hold.trigger, actions.hands[0]),
            Ok(AnalogActionData { active: true, ..Default::default() }));
        actions.digital_value(actions.main.trigger_click, 0, true, true);
        for _ in 0..2 {
            actions.update([true; 2]).unwrap();
            assert!(actions.state(0).is_none());
            assert!(!actions.held.get()[0]);
        }
        actions.digital_value(actions.main.trigger_click, 0, true, false);
        actions.update([true; 2]).unwrap();
        assert!(actions.state(0).is_some());
        actions.digital_value(actions.hold.trigger_click, 0, true, true);
        actions.update([true; 2]).unwrap();
        assert!(actions.held.get()[0]);
        assert!(actions.pressed(0, vrct_openvr::BUTTON_STEAMVR_TRIGGER));
    }

    #[test]
    fn optional_button_availability_change_waits_for_neutral() {
        let actions = Actions::fixture();
        actions.acquire_both();
        actions.digital_value(actions.hold.lower, 0, true, true);
        for _ in 0..2 {
            actions.update([true; 2]).unwrap();
            assert!(actions.state(0).is_none());
            assert!(actions.state(1).is_some());
        }
        actions.digital_value(actions.hold.lower, 0, true, false);
        actions.update([true; 2]).unwrap();
        assert!(actions.state(0).is_some());
        actions.digital_value(actions.hold.trigger_click, 0, true, true);
        actions.update([true; 2]).unwrap();
        assert!(actions.pressed(0, vrct_openvr::BUTTON_STEAMVR_TRIGGER));
    }

    #[test]
    fn failed_update_clears_both_hands_and_resumes_without_high_priority_until_neutral() {
        let actions = Actions::fixture();
        actions.acquire_both();
        actions.input.update_error.set(true);
        assert!(actions.update([true; 2]).is_err());
        assert_eq!(actions.held.get(), [false; 2]);
        assert!(actions.state(0).is_none() && actions.state(1).is_none());
        actions.input.update_error.set(false);
        for hand in 0..2 {
            actions.digital_value(actions.main.trigger_click, hand, true, true);
        }
        for _ in 0..2 {
            actions.update([true; 2]).unwrap();
            assert!(actions.state(0).is_none() && actions.state(1).is_none());
            let updates = actions.input.updates.borrow();
            let sets = updates.last().unwrap();
            assert_eq!(sets.len(), 1);
            assert_eq!(sets[0].action_set, actions.main.handle);
            assert_eq!(sets[0].priority, 0);
        }
        for hand in 0..2 {
            actions.digital_value(actions.main.trigger_click, hand, true, false);
        }
        actions.acquire_both();
        actions.digital_value(actions.hold.grip, 1, true, true);
        actions.update([true; 2]).unwrap();
        assert!(actions.pressed(1, vrct_openvr::BUTTON_GRIP));
    }

    #[test]
    fn hold_acquisition_waits_for_grip_release_but_not_the_stick() {
        let mut snapshot = Snapshot { state: ControllerState::default(), lower: None, available: 0 };
        snapshot.state.button_pressed = 1 << vrct_openvr::BUTTON_GRIP;
        assert!(!snapshot.hold_neutral(), "do not take a grip already held in the game");
        snapshot.state.button_pressed = 0;
        snapshot.state.axis[0] = [0.7, -0.8];
        assert!(snapshot.hold_neutral(), "the stick is not part of the held binding");
        assert!(ready_after(false, Some(snapshot)), "walking does not keep the hand out");
        snapshot.state.button_pressed = 1 << vrct_openvr::BUTTON_GRIP;
        assert!(ready_after(false, Some(snapshot)), "nor holding something in the game");
    }

    #[test]
    fn unavailable_input_is_not_neutral_and_recovery_waits_for_rest() {
        let rest = Snapshot { state: ControllerState::default(), lower: None, available: 0 };
        let mut pressed = rest;
        pressed.state.button_pressed = 1 << vrct_openvr::BUTTON_STEAMVR_TRIGGER;
        assert!(!ready_after(true, None));
        assert!(!ready_after(false, Some(pressed)));
        assert!(ready_after(false, Some(rest)));
        assert!(ready_after(true, Some(pressed)));
        pressed.state.button_pressed = 0;
        pressed.state.axis[1][0] = 0.5;
        // a finger resting on the trigger: back, but no hold taken from the game
        assert!(ready_after(false, Some(pressed)));
        assert!(!pressed.hold_neutral());
        pressed.lower = Some(true);
        assert!(!ready_after(false, Some(pressed)));
    }

    /// Every output names an action of the manifest, and each hand's trigger is in both sets
    #[test]
    fn bindings_use_the_manifests_actions() {
        let names: Vec<String> = manifest()["actions"].as_array().unwrap().iter().map(|a| a["name"].as_str().unwrap().to_string()).collect();
        for c in &CONTROLLERS {
            let b = bindings(c);
            for set in [MAIN, HOLD] {
                let sources = b["bindings"][set]["sources"].as_array().unwrap();
                for source in sources {
                    for (_, out) in source["inputs"].as_object().unwrap() {
                        assert!(names.iter().any(|n| n == out["output"].as_str().unwrap()), "{} {out}", c.kind);
                    }
                }
                for hand in ["left", "right"] {
                    assert!(sources.iter().any(|s| s["path"] == format!("/user/hand/{hand}/input/trigger")), "{} {set} {hand}", c.kind);
                }
            }
            // Locomotion stays with the game; grip is read from the active set while grabbing.
            let held = b["bindings"][HOLD]["sources"].to_string();
            assert!(!held.contains("stick") && !held.contains("trackpad"), "{}", c.kind);
            for set in [MAIN, HOLD] {
                for hand in ["left", "right"] {
                    let grip = b["bindings"][set]["sources"].as_array().unwrap().iter()
                        .find(|s| s["path"] == format!("/user/hand/{hand}/input/grip")).unwrap();
                    assert_eq!(grip["mode"], c.grip_mode, "{}", c.kind);
                    let component = if c.grip_mode == "grab" { "grab" } else { "click" };
                    assert_eq!(grip["inputs"][component]["output"], format!("{set}/in/grip"));
                }
            }
        }
    }
}
