//! The controller shortcut that opens / closes the keyboard: a press of either hand's button
//! (read as the triggers and grips are, so VRChat sees it too: the user picks one that does
//! little there).
use std::time::{Duration, Instant};

const DOUBLE_WITHIN: Duration = Duration::from_millis(400);
const LONG_FOR: Duration = Duration::from_millis(800);

#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
pub enum Shortcut {
    #[default]
    Off,
    /// the stick (touchpad) pressed twice
    StickDouble,
    /// B / Y (the menu button) held
    MenuLong,
    /// B / Y (the menu button) pressed twice
    MenuDouble,
}

impl Shortcut {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "off" => Self::Off,
            "stick_double" => Self::StickDouble,
            "menu_long" => Self::MenuLong,
            "menu_double" => Self::MenuDouble,
            _ => return None,
        })
    }

    /// The button it is pressed with (a bit of ControllerState's button_pressed)
    pub(crate) fn button_mask(self) -> u64 {
        match self {
            Self::Off => 0,
            Self::StickDouble => 1 << vrct_openvr::BUTTON_AXIS0,
            Self::MenuLong | Self::MenuDouble => 1 << vrct_openvr::BUTTON_APPLICATION_MENU,
        }
    }
}

/// One hand's button over the frames
#[derive(Default)]
pub(crate) struct Detector {
    pressed: bool,
    /// when it went down (for the long press), and the first press of a double one
    down_at: Option<Instant>,
    first_press: Option<Instant>,
    fired: bool,
}

impl Detector {
    /// True on the frame the shortcut is made
    pub fn update(&mut self, shortcut: Shortcut, pressed: bool, now: Instant) -> bool {
        let went_down = pressed && !self.pressed;
        self.pressed = pressed;
        if !pressed {
            self.down_at = None;
            self.fired = false;
            return false;
        }
        match shortcut {
            Shortcut::Off => false,
            Shortcut::MenuLong => {
                let down_at = *self.down_at.get_or_insert(now);
                let fire = !self.fired && now.duration_since(down_at) >= LONG_FOR;
                self.fired |= fire;
                fire
            }
            Shortcut::StickDouble | Shortcut::MenuDouble if went_down => {
                let fire = self.first_press.is_some_and(|at| now.duration_since(at) <= DOUBLE_WITHIN);
                self.first_press = if fire { None } else { Some(now) };
                fire
            }
            _ => false,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(shortcut: Shortcut, presses: &[(u64, bool)]) -> Vec<u64> {
        let start = Instant::now();
        let mut d = Detector::default();
        presses.iter().filter(|(ms, pressed)| d.update(shortcut, *pressed, start + Duration::from_millis(*ms))).map(|(ms, _)| *ms).collect()
    }

    #[test]
    fn two_quick_presses_make_it_once_and_slow_ones_do_not() {
        let quick = [(0, true), (100, false), (250, true), (300, true), (350, false), (500, true)];
        assert_eq!(run(Shortcut::MenuDouble, &quick), [250]);
        assert_eq!(run(Shortcut::StickDouble, &[(0, true), (100, false), (600, true), (700, false), (900, true)]), [900]);
    }

    #[test]
    fn holding_makes_it_once_after_the_wait() {
        let held = [(0, true), (500, true), (800, true), (900, true), (1000, false), (1100, true), (1950, true)];
        assert_eq!(run(Shortcut::MenuLong, &held), [800, 1950]);
        assert_eq!(run(Shortcut::MenuLong, &[(0, true), (700, false), (750, true), (1400, true)]), Vec::<u64>::new());
    }

    #[test]
    fn off_never_makes_it() {
        assert!(run(Shortcut::Off, &[(0, true), (50, false), (100, true), (2000, true)]).is_empty());
    }
}
