use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let _main_window = app.get_webview_window("main").unwrap();  // `main_window` is declared here for all builds

            #[cfg(debug_assertions)]
            { _main_window.open_devtools(); }

            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
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


use base64::engine::general_purpose::STANDARD as BASE64;
use base64::Engine;

#[tauri::command]
async fn download_zip_asset(url: String) -> Result<String, String> {
    use reqwest;

    let client = reqwest::Client::new();
    let resp = client.get(&url)
        .header("Accept", "application/octet-stream")
        .send()
        .await.map_err(|e| format!("Request error: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("HTTP error: {}", resp.status()));
    }

    let bytes = resp.bytes().await.map_err(|e| format!("Reading bytes error: {}", e))?;

    Ok(BASE64.encode(&bytes))
}
