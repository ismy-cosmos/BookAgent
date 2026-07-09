use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;

static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// 编译期拿到 `src-tauri/` 的绝对路径，往上两级就是仓库根目录。
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()  // src-tauri/ → frontend/
        .unwrap()
        .parent()  // frontend/ → repo root
        .unwrap()
        .to_path_buf()
}

fn python_executable() -> PathBuf {
    let base = repo_root();
    if cfg!(windows) {
        base.join("bookagent.venv").join("Scripts").join("python.exe")
    } else {
        base.join("bookagent.venv").join("bin").join("python")
    }
}

/// 启动 BookAgent 后端（FastAPI + uvicorn），cwd 设到仓库根目录，
/// 保证 `.chroma` 和所有相对路径的落盘数据跟手动 `python scripts/run_api.py` 一致。
pub fn spawn_backend() {
    let child = Command::new(python_executable())
        .arg("scripts/run_api.py")
        .current_dir(repo_root())
        .spawn()
        .expect("无法启动 BookAgent 后端服务，检查 bookagent.venv 是否已创建（见 setup.sh）");
    *BACKEND_PROCESS.lock().unwrap() = Some(child);
}

pub fn kill_backend() {
    if let Some(mut child) = BACKEND_PROCESS.lock().unwrap().take() {
        let _ = child.kill();
    }
}
