# Issue #66：回答前按需加载对话模型

**日期**：2026-07-29

**状态**：已实现并通过自动化验证；Issue #66 与退出清理保持为两个独立实现单元

**关联 issue**：[#66](https://github.com/ismy-cosmos/BookAgent/issues/66)；
冷热提示缓存输出分叉另见
[#70](https://github.com/ismy-cosmos/BookAgent/issues/70)

## 1. 结论

Issue #66 原表述包含启动预热、readiness 状态机、前端状态、并发等待和多类模型
生命周期，修改面超过当前真实需求。本文以最终需求为准，将实现范围收敛为：

> 用户提交有效问题后、进入真实 `answer()` 前，检查当前配置的对话模型是否已在
> Ollama 中加载；未加载则先同步加载，加载成功后再回答。

本次不在应用启动时预热，不向前端暴露模型状态，不增加 readiness 状态机或新锁。

当前项目没有 per-conversation 模型配置。所有对话使用
`pipeline/api/agent_registry.py` 中的 `BOOKAGENT_MODEL`，因此“本次对话需要的
模型”就是当前配置的 `BOOKAGENT_MODEL`。

本文同时给出“关闭应用后回收 Ollama 显存”的独立工程修复。该修复不再以查清历史
版本差异为实施前提，并且不进入问答、导入、暂停或 Python busy 锁链路。

## 2. 对已有架构和功能的影响

### 2.1 唯一新增行为

每个通过既有业务校验的 `/ask` 请求，在真实回答前执行一次模型驻留检查：

```text
用户提交 /ask
→ 取得现有 busy_state=answering
→ 校验 conversation 存在
→ 校验该书已有可用 chunk
→ 检查 BOOKAGENT_MODEL 是否 loaded
   ├─ 已加载：继续
   └─ 未加载：同步加载，成功后继续
→ 执行现有 get_client() / answer()
→ 成功后写入 conversation turn
→ finally 释放现有 busy_state
```

只有“模型未加载时，首个有效问题会多等待一次模型加载”这一项用户可感知变化。
请求和响应结构、检索、Agent prompt、工具调用、引用、历史写入规则均不改变。

### 2.2 Issue #66 本身明确不修改

- 不修改前端组件、状态、文案或 API 类型；
- 不修改 `/status` 响应；
- 不修改 `busy_state.py`；
- 不修改 `ImportQueue` 或导入处理流程；
- 不增加 `cold/warming/ready/failed` 状态机；
- 不增加 mutex、Condition、等待队列或后台任务；
- 不在应用启动时预热；
- 不主动加载 CPU query embedder；
- 不调整 VLM、导入 embedder 或日常模型释放策略；
- 不修改 FastAPI shutdown；
- 不用退出清理状态参与 Issue #66 的 readiness 判断。

本文第 10 节的退出清理是一个隔离的伴随修复，只修改 Tauri 进程监管层；它不是
Issue #66 问答屏障的一部分。

## 3. 插入位置

`pipeline/api/routes_conversations.py::ask()` 当前顺序是：

1. `busy_state.try_acquire("answering", book_id)`；
2. 读取 conversation；
3. 检查书籍 chunk；
4. 构造 history；
5. `get_client(book_id)`；
6. `answer(question)`；
7. 成功后 `append_turn()`；
8. `finally: busy_state.release()`。

模型检查放在第 4、5 步之间。

这样可以保证：

- 409、404、无内容的 400 请求不会无意义地加载模型；
- 模型加载发生在任何真实 Agent 调用之前；
- 加载失败时不会执行 `answer()`，也不会写入一条不完整历史；
- 所有成功和失败路径继续由现有 `finally` 释放 busy 状态。

不顺便增加空白问题等新的后端校验规则。

## 4. 模型检查和加载

### 4.1 检查

使用 Ollama 原生 `GET /api/ps` 查询当前已加载模型。

检查结果只需要区分：

- `loaded`：`models[].name` 或 `models[].model` 与目标模型匹配；
- `absent`：请求成功、响应合法，但目标模型不存在；
- `error`：连接、超时、HTTP 或响应解析失败。

`error` 不能当作 `absent`。服务状态未知时直接返回现有语义的 503，不继续真实回答。

这里不维护本地 loaded 缓存。Ollama 会独立卸载模型，本地缓存会过期；因此每个有效
问题都在实际使用边界检查一次。

### 4.2 加载

目标模型 absent 时，发送 Ollama 官方支持的空生成请求：

```http
POST /api/generate
Content-Type: application/json

{
  "model": "<BOOKAGENT_MODEL>",
  "stream": false
}
```

该请求不含用户问题、history、system prompt、tools 或书籍内容，不调用 Agent，
不执行检索，也不产生 conversation turn。

空请求成功返回即表示加载操作完成，可以进入真实回答；不再额外建立 readiness
状态机或轮询线程。请求应使用有限超时，失败统一映射到现有的本地模型服务 503。

不显式传递 `keep_alive`，继续沿用 Ollama 服务当前的保留策略。Ollama 官方文档
确认空 `/api/generate` 或 `/api/chat` 可用于预加载模型：
<https://docs.ollama.com/faq>。

### 4.3 Ollama 地址

检查、加载和真实回答必须访问同一个 Ollama 服务。

当前存在一个小的配置不一致：

- `pipeline/ollama_utils.py` 使用 `OLLAMA_BASE_URL`；
- `OllamaAgentClient` 默认使用硬编码的 `http://localhost:11434/v1`。

实现时应从同一个 native base URL 派生 `/v1` 地址，并在 `agent_registry` 创建
client 时显式传入。默认配置行为不变；这不是架构改造，只是避免自定义
`OLLAMA_BASE_URL` 时“检查 A 服务、回答 B 服务”。

## 5. 并发和锁确认

### 5.1 不引入新锁

本设计不需要也不允许新增 readiness lock。

现有 `busy_state` 已经在进程范围内互斥问答和导入。`try_acquire()` 只在读写
`_state` 时短暂持有内部 `threading.Lock`，返回后锁已经释放：

```text
短暂取得 busy_state._lock
→ 设置 _state=answering
→ 释放 busy_state._lock
→ 执行模型 HTTP 检查/加载
→ 执行真实回答
→ finally 再短暂加锁并清除 _state
```

因此模型加载期间不会持有 Python mutex，只保留现有的逻辑忙碌状态。

结果与当前行为一致：

- 第二个 `/ask` 立即得到既有 409，不新增等待语义；
- 导入正在运行时，`/ask` 在模型检查前得到 409；
- 问答加载或回答期间，导入 worker 继续等待 busy 回到 idle；
- 不存在新锁与旧锁的嵌套、反向获取或死锁路径。

### 5.2 与 `ImportQueue._lock` 的关系

`ImportQueue` 只在自己的短锁内尝试取得 `busy_state`，真正 processor 在 queue lock
外执行。新增模型检查既不访问 `ImportQueue._lock`，也不持有
`busy_state._lock` 做网络 I/O，因此不会增加现有锁顺序的任何边。

## 6. 前端确认

前端现有 `useChat.send()` 会在请求发出时设置 `pendingQuestion`，请求结束后才清除；
`ChatPanel` 在这段时间显示问题气泡和现有“思考中”动画。

模型加载位于同一个 `/ask` 请求内，所以加载等待已经被现有 UI 覆盖。本次不新增
“模型加载中”“ready”或“failed”等可见状态，也不修改 `/status`。

## 7. 失败语义

| 场景 | 结果 |
|---|---|
| 模型已加载 | 直接执行现有回答 |
| 模型未加载且空请求成功 | 加载完成后执行现有回答 |
| `/api/ps` 失败或响应非法 | 返回 503；不回答、不写历史 |
| 空加载请求失败或超时 | 返回 503；不回答、不写历史 |
| 检查后被外部进程抢先卸载 | 真实回答可能失败；沿用现有 503，下次问题重新检查 |

所有路径继续由 `/ask` 的现有 `finally` 释放 busy 状态。

## 8. Issue #66 的实际修改范围

实际修改：

- `pipeline/ollama_utils.py`
  - 增加 `/api/ps` 驻留检查；
  - 增加“absent 时空请求加载”的同步 helper；
- `pipeline/api/routes_conversations.py`
  - 在既有校验后、真实回答前调用 helper；
  - 将检查/加载异常映射为现有 503；
- `pipeline/api/agent_registry.py`
  - 让检查和真实 client 使用同一个 Ollama base URL；
- `tests/test_ollama_utils.py`
  - 覆盖 loaded、absent、检查失败和加载失败；
- `tests/api/test_ask.py`
  - 覆盖调用顺序、失败不回答/不写历史、busy 必定释放。

明确不创建 `pipeline/api/readiness.py`，不修改：

- `pipeline/api/busy_state.py`；
- `pipeline/api/import_queue.py`；
- `pipeline/api/ingest_runner.py`；
- `pipeline/api/app.py`；
- `pipeline/api/status.py`、`routes_status.py`；
- `pipeline/embed/embedder.py`；
- `frontend/src/**`；
- `frontend/src-tauri/**`。

第 10 节退出清理的文件范围单独列出，不计入本节。

## 9. 验收标准

自动化测试：

- loaded 时只 probe，不发送空生成请求；
- absent 时顺序为 probe → load → answer → append；
- conversation 不存在或没有 chunk 时不访问 Ollama；
- probe/load 失败时不调用 `answer()`、不写历史，并释放 busy；
- 第二个并发 ask 仍返回 409；
- 导入持有 busy 时 ask 在 probe 前返回 409；
- `/status` 和前端类型不变。

真实验收：

1. 显式卸载 `BOOKAGENT_MODEL`，确认 `/api/ps` 中不存在；
2. 启动 BookAgent，不提问时模型不得被加载；
3. 发出真实问题，确认先完成空加载，再进入真实回答；
4. 前端只显示现有问题气泡和“思考中”；
5. 模型仍驻留时再次提问，确认不重复发送空加载请求；
6. 等 Ollama 自行卸载后再提问，确认同一请求会先恢复模型再回答。

验收目标是“真实 `answer()` 前模型已加载”，不承诺两次回答逐字一致。

### 9.1 真实端到端结果

2026-07-29 使用本机 `cs` 书库和 `qwen3:q4km` 完成三轮真实问答：

1. 首问前 `/api/ps` 为 `{"models":[]}`，GPU 无 compute 进程；
2. 冷启动首问“进程的三种基本状态及转换条件”返回 HTTP 200，总耗时
   14.45 秒；Ollama 日志顺序为
   `GET /api/ps → loading model → POST /api/generate 200 → /v1/chat/completions`；
3. 首问后 `/api/ps` 显示 `qwen3:q4km` 已驻留，`size_vram=5835797298`，
   `nvidia-smi` 显示 runner 占用 7112 MiB；
4. 暖状态第二问“fork() 的父/子/失败返回值”返回 HTTP 200，总耗时 6.01 秒；
5. 暖状态第三问“FIFO 三任务平均周转时间”返回 HTTP 200，总耗时 11.15 秒，
   正确得到 `50/3 ≈ 16.67ms`，并同时调用 retrieve 和 calculate；
6. 后两问各自在回答前执行 `GET /api/ps`，Ollama 日志均为
   `evaluating already loaded`，整个三问期间只有首问前的一次空
   `/api/generate`；
7. 三轮历史均成功落盘。验收结束后已删除临时对话、停止测试 API、显式卸载测试模型；
   最终 `/api/ps` 重新为空，GPU 无 compute 进程。

第二问模型回答中出现“失败时父子进程都返回 -1”的不严谨措辞；严格说法是 fork
失败时不会创建子进程，调用方得到 -1。该现象属于既有回答质量，不影响本节验证的
模型加载屏障、调用顺序或历史提交语义。

随后又用真实桌面应用对 `cs` 连续创建 5 个新会话并提交同一个问题。首问前模型为空，
Ollama 日志再次确认顺序为
`GET /api/ps → loading model → POST /api/generate 200 → /v1/chat/completions`；
后四问只执行 `GET /api/ps` 后进入真实回答，整个应用会话只有首问的一次空
`/api/generate`。五问的 retrieve 结果、顺序和 score 完全相同。

该验证同时发现：Qwen3-VL 在 Ollama 0.32.5 的 cold prefill 和 prompt-cache
复用路径上会稳定生成两种不同答案；`temperature=0`、固定 seed 和尝试传递
`cache_prompt=false` 均不能消除差异。该问题属于 Ollama/llama.cpp 的缓存状态行为，
已独立记录在 #70，不改变 Issue #66“真实回答前模型已经加载”的验收结论，也不在
本实现中采用重载模型、重复回答或扰动 prompt 等高代价绕过。

## 10. 关闭后显存回收：独立工程修复

该修复与 Issue #66 分开实现。目标是让主应用真正退出后主动回收 BookAgent 使用的
Ollama 模型，不再把查清历史版本差异作为实施前置条件。

### 10.1 已确认的当前机制

当前桌面关闭链是：

```text
主窗口 Destroyed
→ frontend/src-tauri/src/lib.rs
→ sidecar::kill_backend()
→ frontend/src-tauri/src/sidecar.rs 对 Python Child 调用 kill()
```

退出链没有向 Ollama 发送 `keep_alive=0`。Ollama 是独立 systemd 服务，不是 Python
sidecar 的子进程，所以 Python 退出后 runner 继续遵循服务级 keep-alive。

2026-07-29 对本机 Ollama `0.32.5` 的受控验证结果是：

- 短生命周期客户端结束后，`qwen3:q4km` 仍驻留并占用 7104 MiB；
- `/api/ps.expires_at` 是请求结束 5 分钟后；
- 显式发送 `keep_alive=0` 后 `/api/ps` 立即为空；
- journal 约 2.06 秒后确认 VRAM 回收完成。

这已经足以支持工程修复。`0.31.1` 与 `0.32.5` 的历史差异仍未完全归因，但不再阻塞
实现。

### 10.2 保持现有强制退出语义

主窗口关闭时的现有产品语义保持不变：

- idle 时直接退出；
- ingesting/answering 时弹现有确认框；
- 取消退出时任务继续；
- 确认退出时销毁全部窗口并强制终止 Python 后端；
- 确认退出不等同于暂停，也不等待导入或回答自然完成。

强杀后的导入恢复依赖现有文件提交边界，不保存一条错误的“已导入历史”：

- chunk 按确定性 ID 分批写入，重跑会查询并跳过已经存在的 ID，只补缺失部分；
- manifest 只在一个文件的 `_store_file()` 全部完成后原子替换写入；
- 若强杀发生在 manifest 前，文件仍在待导入列表，重新提交会补齐该文件；
- 若 manifest 已写但待导入列表尚未来得及删除，重启后会命中“已导入”并自愈移除；
- 因此用户只需重新提交尚未完成的文件批次，不会沿用一条错误的完成记录。

退出清理只处理模型资源，不把强制退出偷偷改成“先暂停再退出”。

### 10.3 工程实现位置

清理由拥有 Python 子进程生命周期的 Tauri/Rust 监管层负责，而不是前端或 FastAPI：

```text
仅主窗口真正 Destroyed
→ 一次性取出 BACKEND_PROCESS，并立即释放该 Mutex
→ kill Python child，做有界 wait/try_wait
→ 后端已停止，不再可能发起新的 Ollama 请求
→ 对 BookAgent 配置的模型发送 keep_alive=0
→ 记录成功或 warning
→ 完成应用退出
```

关键约束：

- 不在持有 `BACKEND_PROCESS` mutex 时等待进程或做 HTTP I/O；
- 不访问 `busy_state`、`ImportQueue._lock` 或 pause event；
- 清理请求有总退出预算，Ollama 不可达时只记录 warning，不允许无限卡住退出；
- 先停止 Python、后卸载模型，避免清理后仍有后台请求把模型重新加载；
- 清理为幂等 one-shot，重复窗口事件不能重复执行退出流程。

建议使用 Rust HTTP client 直接调用 Ollama native API，不依赖已经被终止的 Python
后端，也不通过前端 webview。

### 10.4 清理哪些模型

从与 Python 相同的进程环境读取：

- `OLLAMA_BASE_URL`；
- `BOOKAGENT_MODEL`；
- `VLM_MODEL`。

chat 和 VLM tag 相同时去重，只发一次请求；不执行“卸载 Ollama 中所有模型”的全局
操作。

Ollama API 没有 per-client 模型所有权。如果另一个应用同时使用完全相同的 model
tag，`keep_alive=0` 也会影响它。因此本方案采用桌面单用户前提：

> BookAgent 退出时拥有并可释放自己配置的 chat/VLM model tag。

若未来需要同一 Ollama 服务上的严格多客户端隔离，需要另行建立 model tag 或服务
实例隔离，不能靠 `/api/ps` 推断所有权。

### 10.5 与暂停、窗口和问答功能的隔离

| 用户动作 | 是否触发退出模型清理 | 现有行为 |
|---|---:|---|
| 点击“暂停” | 否 | 继续使用现有 pause event 和安全检查点 |
| 关闭单个聊天子窗口 | 否 | 只关闭该窗口；后端和其他窗口继续 |
| 主窗口忙碌时点关闭后取消 | 否 | 窗口、导入或回答继续 |
| 主窗口忙碌时确认退出 | 是 | 保持现有强杀语义，随后回收 Ollama 模型 |
| 主窗口 idle 时关闭 | 是 | 正常退出并回收 Ollama 模型 |
| Python 后端已经异常退出 | 是 | Rust 仍独立尝试回收模型 |

Tauri `CloseRequested` 仍负责拦截和确认；清理只挂在主窗口已经发生的 `Destroyed`
之后。因此清理不可能在用户取消退出时提前运行。Tauri 2.11.5 将两者定义为不同事件：
<https://docs.rs/tauri/2.11.5/tauri/enum.WindowEvent.html>。

### 10.6 “正在暂停”状态与实际停止边界确认

这里必须区分两个容易混在一起的概念：

1. **前端状态生命周期**：用户点击暂停后，`ImportQueue.request_pause()` 立即设置
   pause event；`ImportPanel` 只要轮询到 `pause_requested=true`，就持续显示禁用的
   “正在暂停…”。这个标志直到整个 `run_ingest()` 处理器返回、worker 清掉
   `_current_task` 后才会清除。因此用户记忆中的“会一直显示正在暂停，直到后台收尾”
   是正确的；500 ms 轮询只会带来很短的显示延迟。
2. **后端停止检查点**：当前实现并不统一等到“当前文件完整解析完”。不同解析器和阶段
   有不同的安全边界；“正在暂停…”表示暂停请求仍在收尾，不等价于当前文件一定会完整
   处理并提交。

当前代码和测试锁定的精确行为如下：

| 暂停发生位置 | 后端何时停 | 当前工作的复用结果 |
|---|---|---|
| 阶段 1 的文件开始前 | 不再开始这个文件及后续文件 | 之前完整解析的文件继续进入后续阶段 |
| EPUB、图片等没有内部暂停检查的解析器 | 当前解析调用完成，下一文件开始前停 | 完整解析结果写入 parse cache |
| 不超过 100 页的 PDF | 当前整份 Marker 调用完成，下一文件开始前停 | 完整解析结果写入 parse cache |
| 超过 100 页、正在分批解析的 PDF | 当前 Marker 页批完成；下一批开始前抛出 `MarkerParsePaused` | 当前 PDF 已累积的批次不写 parse cache，下次从该 PDF 开头重做 |
| WhisperX 转写 | 最多约一个 2 秒轮询周期后终止转写子进程 | WhisperX 没有流式部分结果，当前音频下次从头转写 |
| 阶段 2 的 VLM 图片描述 | 正在执行的单张图片请求先完成；下一张图片开始前停 | 已完成图片逐图写入 VLM cache，未完成文件不入库 |
| 阶段 3 分块、嵌入和入库 | 阶段 3 不读取 pause event | 已进入 `pending` 且图片均已处理的整批文件继续完整提交，不只当前一个文件 |

所以，“暂停中直到当前文件解析完成”只准确描述没有内部检查点的普通解析器和小 PDF，
不是当前实现对所有格式的统一协议。历史上 `ImportQueue` 最初确实以
“file-boundary pause”命名；同一天的最终 ingest 计划又明确增加了 WhisperX 中途
终止和 VLM 图片边界暂停，7 月 21 日的大 PDF 分批实现进一步增加了页批边界暂停。
本节记录的是现在的实现与测试契约，不把最初的概括当成当前统一行为。

暂停已经完成、busy 回到 idle 后再关闭应用，缓存会保留。相关数据均在
`<chroma_dir>/.manifests/` 下落盘，不依赖 Python 进程继续存活：

- `pending_files.json`：未完成文件继续留在待导入列表；
- `parse_cache.json`：已经完整解析、但尚未成功提交的文件保留解析结果；
- `vlm_cache.json`：已经完成的逐图描述保留；
- manifest：只记录完整提交的文件；
- `failures.json`：记录本次 `aborted_early/not_attempted` 结果。

成功提交的文件会主动删除自己的 parse/VLM cache，并从待导入列表移除；这是完成后的
正常清理，不是暂停丢缓存。

`ImportQueue` 的 `progress`、`last_result` 和 pause flag 是运行时 UI 状态，重启后不
保留；恢复入口始终是持久化待导入列表加上述磁盘缓存，而不是自动恢复旧内存任务。

退出模型清理不得读写 `.chroma` 或 `.manifests`，所以不会改变以上缓存语义。
Issue #66 和退出显存清理也不得修改 pause event、上述检查点或“正在暂停…”的显示
生命周期；若产品决定统一改成“所有格式都等当前文件完整完成”，应作为独立功能变更
设计和测试，不能夹带在本计划里。

### 10.7 实际文件与测试

退出修复只修改：

- `frontend/src-tauri/src/sidecar.rs`
  - 后端终止后的有界 Ollama 清理；
  - model tag 去重和错误日志；
- `frontend/src-tauri/Cargo.toml`、`Cargo.lock`
  - 显式声明已有依赖体系中的 Rust HTTP client；
- `frontend/src-tauri/src/sidecar.rs` 内 Rust 单元测试
  - 请求路径和 `keep_alive=0` payload；
  - chat/VLM tag 去重；
  - Ollama 不可达时有界返回；
  - one-shot 退出保护。

已运行现有前端关闭确认、导入暂停、缓存和队列测试，证明没有改变：

- 取消退出；
- 子窗口关闭；
- pause event 生命周期；
- 暂停后的 parse/VLM cache；
- staged files 和完成文件清理。

自动化结果：

- Python 全量可重复测试（排除两个会真实加载 Marker 的 `*_live.py` 文件）：
  `632 passed, 1 skipped`；
- Issue #66、导入、暂停和缓存定向回归：`284 passed`；
- 前端全量 Vitest：`186 passed`；
- Rust：`cargo test` 4 项全部通过，`cargo clippy --all-targets -- -D warnings`
  通过；
- 前端生产构建、TypeScript 检查和 `oxlint` 通过。

## 11. 最终边界

本文包含两个彼此隔离的实现单元：

1. Issue #66：有效问题进入真实 `answer()` 前检查 `BOOKAGENT_MODEL`，未加载则在
   同一请求内同步加载；
2. 退出清理：仅在主窗口真正销毁并终止 Python 后，由 Tauri 监管层有界释放
   BookAgent 配置的 chat/VLM model tag。

两者都不新增前端状态或 Python 锁，不修改暂停/取消协议。退出修复不需要继续强行
追溯历史版本归因；它以可验证的资源回收结果作为验收标准。
