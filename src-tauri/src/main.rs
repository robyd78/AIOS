use std::process::Command;
use tauri::{self, Builder};
use tauri_plugin_dialog::init as dialog_init;
use tauri_plugin_fs::init as fs_init;

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

fn main() {
    Builder::default()
        .plugin(dialog_init())
        .plugin(fs_init())
        .invoke_handler(tauri::generate_handler![launch_app, hypr_dispatch, ingest_prompt])
        .run(tauri::generate_context!())
        .expect("error running AIOS");
}
