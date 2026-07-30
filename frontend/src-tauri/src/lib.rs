mod sidecar;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_http::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      sidecar::spawn_backend();
      Ok(())
    })
    .on_window_event(|window, event| {
      // 只有主窗口的销毁才代表"整个 App 该退出了"；子窗口（import-*/chat-*）
      // 各自关闭不该杀后端、也不该带走其他窗口。
      if window.label() != "main" {
        return;
      }
      if let tauri::WindowEvent::Destroyed = event {
        sidecar::shutdown_backend_and_models();
        // 主窗口没了，把其余还开着的子窗口也一起关掉——Tauri 默认是"所有窗口
        // 都关了才退出"，这里反过来："主窗口一关就该退出"，不等其他窗口。
        for w in window.app_handle().webview_windows().values() {
          if w.label() != "main" {
            let _ = w.destroy();
          }
        }
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
