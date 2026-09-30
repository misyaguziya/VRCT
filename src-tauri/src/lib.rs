use tauri::{Manager, PhysicalPosition, Runtime, WebviewUrl, WebviewWindowBuilder, WindowEvent};
use std::fs::{create_dir_all, OpenOptions};
use std::io::{Error, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

// WebView2は同じプロセス内の全ウィンドウで起動引数が一致している必要があるため、
// tauri.conf.json の main ウィンドウと同じ値にする。Tauri既定の --disable-features に加えて、
// 隠れたウィンドウの描画停止を無効にする (VRパネルは画面外に置いて撮影するため)。
const BROWSER_ARGS: &str = "--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection,CalculateNativeWinOcclusion --disable-backgrounding-occluded-windows --disable-renderer-backgrounding";

// VRオーバーレイに映す画面。Python側 (models/overlay) がタイトルで見つけて撮影・入力する。
// VR UI が ON の間だけ作る (set_vr_panel_window)。OFF の間も動かしておくと、使わない人にも負荷がかかる
fn create_vr_panel_window<R: Runtime, M: Manager<R>>(manager: &M) -> tauri::Result<()> {
    let window = WebviewWindowBuilder::new(manager, "vr_panel", WebviewUrl::App("vr.html".into()))
        .title("VRCT VR Panel")
        // 既定の並び (src-ui/views/vr/vr_layout.json の atlas)。ログの大きさを変えると Python が合わせて変える
        .inner_size(1628.0, 836.0)
        .decorations(false)
        .resizable(false)
        .skip_taskbar(true)
        .focused(false)
        .visible(false)
        .additional_browser_args(BROWSER_ARGS)
        .build()?;
    // 画面外に置く。Windows ではビルダーの .position() が効かず既定の位置 (画面内) に出るため、
    // 作ってから動かし、動かした後で表示する (撮影のため、表示状態で画面外に置いておく)
    window.set_position(PhysicalPosition::new(-10000, -10000))?;
    window.show()?;
    Ok(())
}

fn startup_log_path(executable_path: &Path) -> PathBuf {
    executable_path
        .parent()
        .unwrap_or(Path::new("."))
        .join("logs")
        .join("startup.log")
}

fn startup_log(message: &str) {
    let Ok(executable_path) = std::env::current_exe() else {
        return;
    };
    let log_path = startup_log_path(&executable_path);
    let Some(log_directory) = log_path.parent() else {
        return;
    };
    if create_dir_all(log_directory).is_err() {
        return;
    }
    let Ok(mut log_file) = OpenOptions::new().create(true).append(true).open(log_path) else {
        return;
    };
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_secs());
    let _ = writeln!(log_file, "[{timestamp}] {message}");
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    startup_log("VRCT startup began");
    let result = tauri::Builder::default()
        .setup(|app| {
            let main_window = app.get_webview_window("main").ok_or_else(|| {
                Error::other("main webview window was not created")
            })?;
            main_window.show()?;
            if let Err(error) = main_window.set_focus() {
                startup_log(&format!("Main window focus failed: {error}"));
            }
            startup_log("Main window is ready");

            #[cfg(debug_assertions)]
            { main_window.open_devtools(); }

            Ok(())
        })
        // 画面外の vr_panel ウィンドウが残ることがあるため「最後のウィンドウが閉じたら終了」に頼れない。
        // main が閉じたらアプリを終了する。
        .on_window_event(|window, event| {
            if window.label() == "main" && matches!(event, WindowEvent::Destroyed) {
                window.app_handle().exit(0);
            }
        })
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![get_font_list, download_zip_asset, set_vr_panel_window])
        .run(tauri::generate_context!());
    match result {
        Ok(()) => startup_log("VRCT event loop ended"),
        Err(error) => {
            startup_log(&format!("VRCT startup failed: {error}"));
            panic!("error while running tauri application: {error}");
        }
    }
}


// VR UI の ON/OFF に合わせて、VR画面のウィンドウを作る・消す (メイン画面が設定に合わせて呼ぶ)。
// ウィンドウを作るので async にする (同期コマンドから作ると Windows で固まることがある)
#[tauri::command]
async fn set_vr_panel_window(app: tauri::AppHandle, open: bool) -> Result<(), String> {
    match (open, app.get_webview_window("vr_panel")) {
        (true, None) => create_vr_panel_window(&app).map_err(|error| {
            startup_log(&format!("VR panel window creation failed: {error}"));
            error.to_string()
        }),
        (false, Some(window)) => window.destroy().map_err(|error| error.to_string()),
        _ => Ok(()),
    }
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

#[cfg(test)]
mod tests {
    use super::startup_log_path;
    use std::path::Path;

    #[test]
    fn startup_log_is_stored_next_to_the_application() {
        assert_eq!(
            startup_log_path(Path::new(r"C:\VRCT\VRCT.exe")),
            Path::new(r"C:\VRCT\logs\startup.log")
        );
    }
}
