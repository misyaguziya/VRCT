// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

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
        .on_window_event(|event| { // This is for fix the bug that the window scaling issue when dragging between monitors.
            if let tauri::WindowEvent::ScaleFactorChanged { new_inner_size, .. } = event.event() {
                event.window().set_size(tauri::Size::Physical(*new_inner_size)).unwrap();
            }
        })
        .invoke_handler(tauri::generate_handler![get_font_list, download_zip_asset])
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

#[tauri::command]
async fn download_zip_asset(url: String) -> Result<String, String> {
    use reqwest;
    // reqwest のクライアントを作成
    let client = reqwest::Client::new();
    // GET リクエストを送信（リダイレクトも自動追従します）
    let resp = client.get(&url)
        .header("Accept", "application/octet-stream")
        .send()
        .await.map_err(|e| format!("Request error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("HTTP error: {}", resp.status()));
    }
    // レスポンスのバイナリデータを取得
    let bytes = resp.bytes().await.map_err(|e| format!("Reading bytes error: {}", e))?;
    // バイナリデータを base64 エンコードして返す
    Ok(base64::encode(&bytes))
}