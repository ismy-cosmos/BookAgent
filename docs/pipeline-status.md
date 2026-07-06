# 核心管线状态与待办优先级

追踪主干链路 解析 → 分块 → 元数据 → 入向量库 → 检索召回 的实时状态，以及下一步该修哪个 issue。随代码推进持续更新，不是一次性快照。

## 各阶段状态

- **解析 → 分块 → 元数据**：已完成。
- **入向量库**：写库代码（`ChromaStore.add_chunks` / `scripts/ingest.py`）已用真实数据端到端验证过（单张真实图片、单个真实音频文件分别端到端 ingest 成功，内容与元数据正确）；批量多文件场景下的单文件失败容错还没有（issue #6），整本书级别的正式 ingest 待 #6 落地后再做。
- **检索召回**：`RealExecutor` 已落地（PR #15，`feat/realexecutor-retrieval` 分支），`retrieve`/`get_chunk` 走真实 `ChromaStore`/`Embedder`，不再是 `StubExecutor` 硬编码假数据。
- **VLM/Ollama 调用方式**：`VLMImageParser`/`check_vision.py` 已统一改用 `openai` SDK（PR #21），修掉了顺带发现的 VRAM 判断阈值过时问题，`VLMImageParser` 用完模型会主动释放显存，避免跟 embedder 抢 GPU。
- **AudioParser**：已改用项目自己独立的 `whisperx.venv` + Python API wrapper（PR #22），不再依赖 `BookAgent-Baseline` 仓库路径。

## 待办 issue 优先级顺序

1. **下一步：issue #6**（`scripts/ingest.py` 核心编排逻辑零测试覆盖，批量处理无单文件失败容错）。这是关键路径——要可靠地把真实书批量灌进向量库，必须先有这层容错，否则一批文件里一个坏 PDF/WhisperX 崩/Ollama 连不上就会中断整批。
2. **之后：issue #13 + #14 一起做**：
   - #13：内嵌复杂 atomic（图/表/公式）未路由给 VLM 理解。
   - #14：VLM 图片预处理缺失，大尺寸图可能导致视觉 token 溢出上下文窗口。
   - 两者都会改变 VLM 这条链路最终产出的内容，一起做完再验证。#18（prompt/num_predict 调速）延后，不挤占这一批。
3. **再之后：issue #11 + #10**：
   - #11：EPUB 容器直接子级裸文本节点丢失，内联标签经兜底分支产生碎片元素。
   - #10：`audio.py` WhisperX 短 VAD segment 直接成 chunk，未走 chunker 打包逻辑。
   - 这两项加上 #13 都会改变最终入库的 chunk 内容，建议攒到一起做完、再统一跑一次评测级正式 ingest，避免中途多次重灌向量库。