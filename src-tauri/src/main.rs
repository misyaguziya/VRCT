// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// use tauri::command;
use tauri::Manager;
use window_shadows::set_shadow;
fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let main_window = app.get_window("main").unwrap();  // `main_window` is declared here for all builds

            #[cfg(debug_assertions)]
            { main_window.open_devtools(); }

            #[cfg(any(windows, target_os = "macos"))]
            set_shadow(main_window, true).unwrap();

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_font_list])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}


use font_kit::{source::SystemSource};
use std::collections::HashSet;

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
