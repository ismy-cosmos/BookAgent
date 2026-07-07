# 核心管线状态与待办优先级

追踪主干链路 解析 → 分块 → 元数据 → 入向量库 → 检索召回 的实时状态，以及下一步该修哪个 issue。随代码推进持续更新，不是一次性快照。

## 各阶段状态

- **解析 → 分块 → 元数据**：已完成。
- **入向量库**：写库代码（`ChromaStore.add_chunks` / `scripts/ingest.py`）已用真实数据端到端验证过（单张真实图片、单个真实音频文件分别端到端 ingest 成功，内容与元数据正确）；批量多文件场景下的单文件失败容错+回滚+连续失败熔断已完成（PR #23），整本书级别的正式 ingest 待内嵌图片 VLM 描述回填落地后再做。
- **检索召回**：`RealExecutor` 已落地（PR #15，`feat/realexecutor-retrieval` 分支），`retrieve`/`get_chunk` 走真实 `ChromaStore`/`Embedder`，不再是 `StubExecutor` 硬编码假数据。
- **VLM/Ollama 调用方式**：`VLMImageParser`/`check_vision.py` 已统一改用 `openai` SDK（PR #21），修掉了顺带发现的 VRAM 判断阈值过时问题，`VLMImageParser` 用完模型会主动释放显存，避免跟 embedder 抢 GPU。
- **AudioParser**：已改用项目自己独立的 `whisperx.venv` + Python API wrapper（PR #22），不再依赖 `BookAgent-Baseline` 仓库路径。
- **内嵌图片 VLM 描述回填**：已实现（`feat/vlm-figure-routing` 分支，尚未合并）——PDF/EPUB 内嵌图与独立图片文件统一在 ingest 的 VLM 批量阶段生成描述回填 chunk 正文，发送前 resize（长边 2048px 上限，真实 GPU 实测防显存溢出），单图失败降级、连续失败熔断（默认 3 张、跨批次计数）。待完成真实数据端到端审读后合并。

## 待办 issue 优先级顺序

**已完成**：issue #6（`scripts/ingest.py` 批量单文件失败容错+回滚+连续失败熔断，PR #23）、issue #16（8GB 显卡 mmproj 上不了 GPU 是 Ollama 自身回归 bug，已升级版本修复）。

1. **进行中（代码已完成，待真实数据审读后合并）：issue #13 + #14**：
   - #13：内嵌图片 VLM 描述回填（PDF 内嵌图 + EPUB img + 独立图片文件）。代码在 `feat/vlm-figure-routing` 分支，三阶段 ingest 架构（解析→VLM 批量→入库），6 个 commit、309 测试全绿。table/formula 页面级复杂度分类器留给未来。
   - #14：VLM 图片发送前 resize（长边上限 2048px，真实 GPU 干净隔离实测：2048px 正常、3072px 起 `cudaMalloc failed`），与 num_ctx 无关。
   - 下一步：对项目内全部 PDF/EPUB 语料跑真实数据端到端审读，确认 VLM 描述质量后合并。#18（prompt/num_predict 调速）延后。
2. **再之后：issue #11 + #10**：
   - #11：EPUB 容器直接子级裸文本节点丢失，内联标签经兜底分支产生碎片元素。
   - #10：`audio.py` WhisperX 短 VAD segment 直接成 chunk，未走 chunker 打包逻辑。
   - 这两项加上 #13 都会改变最终入库的 chunk 内容，建议攒到一起做完、再统一跑一次评测级正式 ingest，避免中途多次重灌向量库。
3. **尚未排期/未三角分类**：issue #17（agent 溯源可靠性：问题简单时不 retrieve + 伪造历史引用）、#19（Chunker 句子边界判断评估替换为成熟分句库）、#20（8GB 显卡上 ingest 进程与聊天进程抢占同一块 GPU 显存，需要产品侧先明确是否支持边聊天边导入书籍）。