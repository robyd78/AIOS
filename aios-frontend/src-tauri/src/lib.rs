use std::process::Command;

#[tauri::command]
fn launch_app(cmd: String, args: Vec<String>) -> Result<(), String> {
  Command::new("sh")
    .arg("-lc")
    .arg(format!("{} {}", cmd, shell_words::join(args)))
    .spawn()
    .map_err(|e| e.to_string())?;
  Ok(())
}

#[tauri::command]
fn hypr_dispatch(args: Vec<String>) -> Result<String, String> {
  let output = Command::new("hyprctl")
    .arg("dispatch")
    .args(&args)
    .output()
    .map_err(|e| e.to_string())?;
  Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

#[tauri::command]
fn ingest_prompt(text: String) -> Result<String, String> {
  Ok(format!("You said: {}", text))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![launch_app, hypr_dispatch, ingest_prompt])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
