// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// use tauri::command;
use tauri::Manager;
fn main() {
    tauri::Builder::default()
        .setup(|app| {
            #[cfg(debug_assertions)]
            app.get_window("main").unwrap().open_devtools(); // `main` is the first window from tauri.conf.json without an explicit label
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_font_list])
        // .invoke_handler(tauri::generate_handler![greet, run_python_script])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");

}

use std::fs;
use std::env;

#[tauri::command]
fn get_font_list() -> Vec<String> {
    // システム全体のフォントディレクトリ
    let system_font_dir = "C:\\Windows\\Fonts";
    // ユーザーローカルのフォントディレクトリ
    let local_font_dir = format!("{}\\Microsoft\\Windows\\Fonts", env::var("LOCALAPPDATA").unwrap());

    let mut fonts = Vec::new();

    // システムフォントとユーザーフォントのディレクトリをチェック
    let font_dirs = vec![system_font_dir, &local_font_dir];

    for dir in font_dirs {
        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries {
                if let Ok(entry) = entry {
                    let path = entry.path();
                    if let Some(extension) = path.extension() {
                        if extension == "ttf" || extension == "otf" {
                            if let Some(font_name) = path.file_stem() {
                                fonts.push(font_name.to_string_lossy().to_string());
                            }
                        }
                    }
                }
            }
        }
    }

    fonts
}
