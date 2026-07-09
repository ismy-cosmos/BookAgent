use std::process::{Child, Command};
use std::sync::Mutex;

static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

fn python_executable() -> &'static str {
    if cfg!(windows) {
        "../../bookagent.venv/Scripts/python.exe"
    } else {
        "../../bookagent.venv/bin/python"
    }
}

/// 开发模式下（`npm run tauri dev`）Rust 进程的 cwd 是 `frontend/src-tauri/`，
/// 所以用相对路径 `../../` 回到仓库根目录找 venv 和脚本。
/// 生产打包后的路径解析方式是独立的未决问题（见 spec 第 11 节），这里先只保证开发模式能跑。
pub fn spawn_backend() {
    let child = Command::new(python_executable())
        .arg("../../scripts/run_api.py")
        .spawn()
        .expect("无法启动 BookAgent 后端服务，检查 bookagent.venv 是否已创建（见 setup.sh）");
    *BACKEND_PROCESS.lock().unwrap() = Some(child);
}

pub fn kill_backend() {
    if let Some(mut child) = BACKEND_PROCESS.lock().unwrap().take() {
        let _ = child.kill();
    }
}
