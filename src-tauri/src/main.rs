use tauri::Manager;
use window_shadows::set_shadow;
use windows::Win32::UI::WindowsAndMessaging::{GetForegroundWindow, GetWindowTextW};
use std::collections::HashSet;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let main_window = app.get_window("main").unwrap();  // `main_window` is declared here for all builds

            #[cfg(debug_assertions)]
            { main_window.open_devtools(); }

            #[cfg(any(windows, target_os = "macos"))]
            set_shadow(main_window, true).unwrap()

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_font_list, get_active_window_title])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

use font_kit::{source::SystemSource};

#[tauri::command]
async fn get_font_list() -> Vec<String> {
    let source = SystemSource::new();
    let mut font_families = HashSet::new();

    if let Ok(fonts) = source.all_fonts() {
        for font in fonts {
            if let Ok(info) = font.load() {
                font_families.insert(info.family_name().to_string());
            }
        }
    }

    font_families.into_iter().collect()
}

use windows::Win32::Foundation::HWND;
#[tauri::command]
fn get_active_window_title() -> String {
    unsafe {
        // Get the handle of the foreground (active) window
        let hwnd = GetForegroundWindow();
        if hwnd == HWND(0) {  // `HWND(0)` は null ハンドルを表します
            return "No active window".to_string();
        }

        // Create a buffer to hold the window title
        let mut buffer: [u16; 512] = [0; 512];

        // Get the window title
        let length = GetWindowTextW(hwnd, &mut buffer);

        if length > 0 {
            // Convert the result to a Rust string
            return String::from_utf16_lossy(&buffer[..length as usize]);
        }
    }
    "Failed to retrieve window title".to_string()
}
