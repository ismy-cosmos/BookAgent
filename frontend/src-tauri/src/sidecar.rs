use std::collections::HashSet;
use std::env;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

static BACKEND_PROCESS: Mutex<Option<Child>> = Mutex::new(None);
static SHUTDOWN_STARTED: AtomicBool = AtomicBool::new(false);

const BACKEND_EXIT_TIMEOUT: Duration = Duration::from_secs(2);
const BACKEND_EXIT_POLL_INTERVAL: Duration = Duration::from_millis(25);
const OLLAMA_CLEANUP_BUDGET: Duration = Duration::from_secs(3);
const OLLAMA_CONNECT_TIMEOUT: Duration = Duration::from_millis(500);
const DEFAULT_OLLAMA_BASE_URL: &str = "http://localhost:11434";
const DEFAULT_CHAT_MODEL: &str = "qwen3:q4km";
const DEFAULT_VLM_MODEL: &str = "qwen3:q4km";

/// 编译期拿到 `src-tauri/` 的绝对路径，往上两级就是仓库根目录。
fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent() // src-tauri/ → frontend/
        .unwrap()
        .parent() // frontend/ → repo root
        .unwrap()
        .to_path_buf()
}

fn python_executable() -> PathBuf {
    let base = repo_root();
    if cfg!(windows) {
        base.join("bookagent.venv")
            .join("Scripts")
            .join("python.exe")
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

fn begin_shutdown(flag: &AtomicBool) -> bool {
    !flag.swap(true, Ordering::AcqRel)
}

fn take_backend_process() -> Option<Child> {
    // Explicit block guarantees that the process mutex is released before
    // kill/wait and before any Ollama HTTP request.
    let mut process = BACKEND_PROCESS.lock().unwrap();
    process.take()
}

fn wait_for_backend_exit(child: &mut Child, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    loop {
        match child.try_wait() {
            Ok(Some(_status)) => return true,
            Ok(None) if Instant::now() < deadline => {
                thread::sleep(BACKEND_EXIT_POLL_INTERVAL);
            }
            Ok(None) => return false,
            Err(error) => {
                log::warn!("检查 Python 后端退出状态失败: {error}");
                return false;
            }
        }
    }
}

fn stop_backend() {
    let Some(mut child) = take_backend_process() else {
        return;
    };

    if let Err(error) = child.kill() {
        // The child may already have exited independently. try_wait below
        // still reaps it and distinguishes that harmless case from failure.
        log::warn!("终止 Python 后端时返回错误（可能已经退出）: {error}");
    }
    if !wait_for_backend_exit(&mut child, BACKEND_EXIT_TIMEOUT) {
        log::warn!(
            "Python 后端在 {:?} 内未确认退出，继续执行有界 Ollama 清理",
            BACKEND_EXIT_TIMEOUT
        );
    }
}

fn deduplicate_model_tags(chat_model: &str, vlm_model: &str) -> Vec<String> {
    let mut seen = HashSet::new();
    [chat_model, vlm_model]
        .into_iter()
        .filter(|model| !model.is_empty() && seen.insert(*model))
        .map(str::to_owned)
        .collect()
}

fn configured_models() -> Vec<String> {
    let chat_model = env::var("BOOKAGENT_MODEL").unwrap_or_else(|_| DEFAULT_CHAT_MODEL.to_owned());
    let vlm_model = env::var("VLM_MODEL").unwrap_or_else(|_| DEFAULT_VLM_MODEL.to_owned());
    deduplicate_model_tags(&chat_model, &vlm_model)
}

fn unload_models(
    base_url: &str,
    models: &[String],
    budget: Duration,
) -> Vec<(String, Result<(), String>)> {
    let started = Instant::now();
    let client = match reqwest::blocking::Client::builder()
        .connect_timeout(OLLAMA_CONNECT_TIMEOUT.min(budget))
        .no_proxy()
        .build()
    {
        Ok(client) => client,
        Err(error) => {
            return models
                .iter()
                .map(|model| {
                    (
                        model.clone(),
                        Err(format!("无法创建 Ollama 清理客户端: {error}")),
                    )
                })
                .collect();
        }
    };
    let endpoint = format!("{}/api/generate", base_url.trim_end_matches('/'));

    models
        .iter()
        .map(|model| {
            let elapsed = started.elapsed();
            let Some(remaining) = budget.checked_sub(elapsed) else {
                return (model.clone(), Err("Ollama 清理总时间预算已耗尽".to_owned()));
            };
            if remaining.is_zero() {
                return (model.clone(), Err("Ollama 清理总时间预算已耗尽".to_owned()));
            }

            let payload = serde_json::json!({
                "model": model,
                "keep_alive": 0,
            });
            let result = client
                .post(&endpoint)
                .header(reqwest::header::CONTENT_TYPE, "application/json")
                .timeout(remaining)
                .body(payload.to_string())
                .send()
                .map_err(|error| error.to_string())
                .and_then(|response| {
                    if response.status().is_success() {
                        Ok(())
                    } else {
                        Err(format!("Ollama 返回 HTTP {}", response.status()))
                    }
                });
            (model.clone(), result)
        })
        .collect()
}

/// Main-window-only shutdown path: stop Python first, then make a bounded,
/// best-effort attempt to unload BookAgent's configured Ollama models.
pub fn shutdown_backend_and_models() {
    if !begin_shutdown(&SHUTDOWN_STARTED) {
        return;
    }

    stop_backend();

    let base_url =
        env::var("OLLAMA_BASE_URL").unwrap_or_else(|_| DEFAULT_OLLAMA_BASE_URL.to_owned());
    for (model, result) in unload_models(&base_url, &configured_models(), OLLAMA_CLEANUP_BUDGET) {
        match result {
            Ok(()) => log::info!("已请求 Ollama 卸载模型: {model}"),
            Err(error) => log::warn!("退出时卸载 Ollama 模型 {model} 失败: {error}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};
    use std::net::TcpListener;

    #[test]
    fn model_tags_are_deduplicated_without_changing_order() {
        assert_eq!(
            deduplicate_model_tags("chat:latest", "chat:latest"),
            vec!["chat:latest"]
        );
        assert_eq!(
            deduplicate_model_tags("chat:latest", "vision:latest"),
            vec!["chat:latest", "vision:latest"]
        );
    }

    #[test]
    fn shutdown_guard_is_one_shot() {
        let flag = AtomicBool::new(false);
        assert!(begin_shutdown(&flag));
        assert!(!begin_shutdown(&flag));
    }

    #[test]
    fn unload_posts_native_generate_keep_alive_zero() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        let server = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            stream
                .set_read_timeout(Some(Duration::from_secs(2)))
                .unwrap();
            let mut request = Vec::new();
            let mut buffer = [0_u8; 1024];
            loop {
                let count = stream.read(&mut buffer).unwrap();
                if count == 0 {
                    break;
                }
                request.extend_from_slice(&buffer[..count]);
                let text = String::from_utf8_lossy(&request);
                let Some(header_end) = text.find("\r\n\r\n") else {
                    continue;
                };
                let content_length = text[..header_end]
                    .lines()
                    .find_map(|line| {
                        line.to_ascii_lowercase()
                            .strip_prefix("content-length:")
                            .map(str::trim)
                            .and_then(|value| value.parse::<usize>().ok())
                    })
                    .unwrap_or(0);
                if request.len() >= header_end + 4 + content_length {
                    break;
                }
            }
            stream
                .write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}")
                .unwrap();
            String::from_utf8(request).unwrap()
        });

        let results = unload_models(
            &format!("http://{address}/"),
            &["qwen3:q4km".to_owned()],
            Duration::from_secs(2),
        );
        let request = server.join().unwrap();

        assert_eq!(results, vec![("qwen3:q4km".to_owned(), Ok(()))]);
        assert!(request.starts_with("POST /api/generate HTTP/1.1\r\n"));
        let body = request.split("\r\n\r\n").nth(1).unwrap();
        let payload: serde_json::Value = serde_json::from_str(body).unwrap();
        assert_eq!(payload["model"], "qwen3:q4km");
        assert_eq!(payload["keep_alive"], 0);
    }

    #[test]
    fn unreachable_ollama_returns_within_budget() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        drop(listener);

        let started = Instant::now();
        let results = unload_models(
            &format!("http://{address}"),
            &["qwen3:q4km".to_owned()],
            Duration::from_millis(250),
        );

        assert!(started.elapsed() < Duration::from_secs(2));
        assert!(results[0].1.is_err());
    }
}
