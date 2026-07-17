# 后续独立项路线图

记录明确排在当前里程碑之后、尚无实现计划的独立工作项。每项列出背景依据和现有铺垫，避免下次拾起时重新讨论一遍。

## 前端（原生桌面程序）

`RealExecutor` 落地时（`feat/realexecutor-retrieval` 分支）已经决定本次纯 Python 打底，前端拆成下一个独立子项目。**MVP 已完成并合并**，本节保留历史决策记录；当前进行中的多窗口大改见下方"进度"小节。

- **形态约束（2026-07-07 确认）**：前端必须是原生桌面程序，不能是"打开浏览器看网页"的形态；即便底层用 webview 渲染也可以，只要呈现为独立原生窗口（没有浏览器地址栏/标签页）。
- **技术选型（2026-07-07 确认）**：Tauri（Rust 外壳 + TS/网页前端渲染）。经可视化界面对比后用户选定，理由是视觉效果上限更高。前端（TS/Rust）与后端（Python）语言不通，新增了一层本地 HTTP 契约连接 `answer()`——FastAPI sidecar 常驻子进程，`127.0.0.1` 固定端口，非流式。
- **MVP 范围（2026-07-07 确认，已交付）**：问答对话（多轮）+ 引用来源展示 + 完整书籍管理（前端内导入新文件/新建 `book_id` + 删除书籍）。`ChromaStore.delete_collection` 已补上。
- 已打好的接缝：`pipeline/agent/answer.py` 的 `answer()` 无状态入口 + `AnswerResult`/`ChatTurn`/`Citation` dataclass。
- 范围提醒：官方任务书对交互的硬性要求只是"一键对话启动"，CLI（`scripts/ask_cli.py`）已经满足。GUI 前端对应评审维度里的"产品思维/用户体验闭环"，是加分项，不是必需交付物——排期时不要让它挤占被打分的核心管线与评测。

### 进度（2026-07-17）

- **后端 HTTP 层 + GPU 并发互斥锁（issue #20）+ 异步导入队列（issue #27）+ 前端 Plan A/B**：全部完成并合并进 `dev`（[PR #28](https://github.com/ismy-cosmos/BookAgent/pull/28)、[PR #29](https://github.com/ismy-cosmos/BookAgent/pull/29)、[PR #30](https://github.com/ismy-cosmos/BookAgent/pull/30)、[PR #31](https://github.com/ismy-cosmos/BookAgent/pull/31)）。同一批还修复了 chromadb 并发构造 bug、RAG 历史引用泄露/伪造 bug（issue #17 当时的初版修复；真实评测里后来又发现新的溯源可靠性问题，见下方 issue #17/#40），npm→pnpm 迁移完成。
- **GPU 互斥锁单向防护缺口已修复**：曾经的已知缺口——回答生成期间无法阻止新导入开始——已通过 issue #36（忙碌锁改双向互斥+导入前释放 Ollama 驻留模型）修复，[PR #39](https://github.com/ismy-cosmos/BookAgent/pull/39)，2026-07-16 合并，issue 已关闭。
- **前端多窗口大改：已全部完成并合并**。首页书库网格 + "导入文件"/"开始对话"独立 Tauri 窗口 + 对话窗口聊天气泡样式，四个计划全部落地：计划1 后端基础（[PR #32](https://github.com/ismy-cosmos/BookAgent/pull/32)）、计划2 窗口壳层+首页（[PR #33](https://github.com/ismy-cosmos/BookAgent/pull/33)）、计划3 导入文件窗口（[PR #35](https://github.com/ismy-cosmos/BookAgent/pull/35)）、计划4 对话窗口重做（[PR #37](https://github.com/ismy-cosmos/BookAgent/pull/37)）。对话窗口 markdown 渲染同批补上（[PR #38](https://github.com/ismy-cosmos/BookAgent/pull/38)）。遗留的前端代码卫生项（`components/` 按领域重组、`../` import 改 `@` 别名）也已收尾（PR #46、#47）。
- **`ask` 接口改流式（2026-07-10 讨论，明确排除在这次多窗口大改之外）**：现有 `POST .../ask` 是同步接口，等模型把多轮工具调用+最终回答全部跑完才一次性返回，所以"关闭对话窗口就中断回答"这种效果做不到——这本质是流式架构才有的副作用（连接断开→服务端检测到没人收→停止继续生成），不是加个取消接口能简单补上的。要做到这个效果需要把 `ask` 改成 SSE/chunked 流式响应，`OllamaAgentClient` 支持流式输出，前端气泡改成逐字/逐块更新——后端+前端都要改，是一个真正的新能力，不是小修复。这次多窗口大改明确决定不做，先接受"关窗口后台照跑、回答仍会存进对话历史"这个现状（跟已有的"关闭子窗口不打断后端"设计一致）。触发条件：产品侧明确要"打字机效果"或"关窗口真的能停止生成"时再排期。

## reranker 精排

属于项目理解方案 W3 里程碑的消融实验项（附录 B.4 的 E2：关闭 rerank），不在当前 W2 阶段范围内。

- 设计基线：召回用 bge-m3（dense 1024 维），精排用 bge-reranker-v2-m3，两段式。
- 现状：全项目只有召回（`RealExecutor.retrieve` 直接用 dense 向量相似度排序），精排代码一行没有。
- 何时启动：等 W3 里程碑排上日程，作为消融实验的一部分对比"开/关 rerank"对 Token 消耗和 Hit@5 的影响。

## 混合类型检索排序优化

依赖 issue #13（内嵌复杂 atomic 未路由给 VLM）先落地。

- 现状：检索结果按 dense 向量相似度统一排序，不区分 `element_type`（正文/表格/公式/图片）。
- 问题：figure 类型 chunk 在 #13 落地前只是 `![](path)` 占位符，语义几乎为零，混在正文结果里可能拉低整体检索质量；#13 落地后 figure 变成真实 VLM 描述，排序策略可能需要重新评估（比如是否要对不同 element_type 做差异化的相关性加权）。
- 待办：#13 完成、有真实的 VLM 描述内容后，用真实数据评估现有纯 dense 排序是否够用，再决定要不要引入额外排序信号。

## book_id 跨书全局检索

当前设计明确是单书锚定（`docs/book-management.md`）：一本书一个 Chroma collection，`RealExecutor` 构造期固定 `book_id`，检索永远打对应 collection，不跨书。

- 如果未来产品上需要"在我整个书库里搜"这个能力，在 collection-per-book 模型下要循环遍历各 collection 分别查询再合并结果，目前完全没有设计、没有代码。
- 触发条件：产品侧明确提出这个需求后再评估，当前不是任何里程碑的一部分。