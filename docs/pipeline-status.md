# 核心管线状态与待办优先级

追踪主干链路 解析 → 分块 → 元数据 → 入向量库 → 检索召回 的实时状态，以及下一步该修哪个 issue。随代码推进持续更新，不是一次性快照。

## 各阶段状态

- **解析 → 分块 → 元数据**：已完成。
- **入向量库**：写库代码（`ChromaStore.add_chunks` / `scripts/ingest.py`）已用真实数据端到端验证过；批量多文件场景下的单文件失败容错+回滚+连续失败熔断已完成（PR #23）；三阶段架构（解析→VLM批量描述→入库，PR #26）已合并，整本书级别的正式 ingest 链路完整打通。
- **检索召回**：`RealExecutor` 已落地（PR #15，`feat/realexecutor-retrieval` 分支），`retrieve`/`get_chunk` 走真实 `ChromaStore`/`Embedder`，不再是 `StubExecutor` 硬编码假数据。
- **VLM/Ollama 调用方式**：`VLMImageParser`/`check_vision.py` 已统一改用 `openai` SDK（PR #21），修掉了顺带发现的 VRAM 判断阈值过时问题，`VLMImageParser` 用完模型会主动释放显存，避免跟 embedder 抢 GPU。
- **AudioParser**：已改用项目自己独立的 `whisperx.venv` + Python API wrapper（PR #22），不再依赖 `BookAgent-Baseline` 仓库路径。
- **内嵌图片 VLM 描述回填**：已完成并合并（PR #26，`feat/vlm-figure-routing`）——PDF/EPUB 内嵌图与独立图片文件统一在 ingest 的 VLM 批量阶段生成描述回填 chunk 正文，发送前 resize（长边 2048px 上限，真实 GPU 实测防显存溢出），单图失败降级、连续失败熔断（默认 3 张、跨批次计数）。真实数据端到端审读见`docs/test-report-2026-07-06-vlm-figure-routing.md`：40张图100%成功、真实token消耗45286（均1132/图），发现两项质量问题（caption重复、极小图片幻觉，见issue #25）留待后续处理，不阻塞。

## 待办 issue 优先级顺序

**已完成**：issue #6（`scripts/ingest.py` 批量单文件失败容错+回滚+连续失败熔断，PR #23）、issue #16（8GB 显卡 mmproj 上不了 GPU 是 Ollama 自身回归 bug，已升级版本修复）、**issue #13 + #14**（内嵌图片 VLM 描述回填 + resize，PR #26，2026-07-07 合并）、**issue #20**（GPU 显存互斥锁：`ImportQueue` 单工作线程 FIFO 队列+忙碌状态接入问答/删除接口，PR #28，2026-07-08 合并，issue 已关闭）、**issue #27**（ingest 异步执行+进度上报：`run_ingest()` 可复用化+解析/VLM双缓存+暂停支持（PR #29）、`ImportQueue` 真实接入+待导入文件列表+进度/暂停/取消 HTTP 接口（PR #30），2026-07-09 全部合并，issue 已关闭）。

1. **下一步：issue #17**（agent 溯源可靠性：问题简单时不 retrieve + 伪造历史引用）。真实数据 QA 端到端验收时重新复现并追加了证据（`_format_turn_for_replay` 格式被模仿，可凭空编造不存在的文件名），优先级提前——"VLM 图片理解对最终问答质量的实际贡献"这件事目前无法验证，每次尝试都被这个 bug 拦住（该调用 retrieve 时模型跳过了）。
2. **之后：issue #11 + #10**：
   - #11：EPUB 容器直接子级裸文本节点丢失，内联标签经兜底分支产生碎片元素。
   - #10：`audio.py` WhisperX 短 VAD segment 直接成 chunk，未走 chunker 打包逻辑。
   - 这两项都会改变最终入库的 chunk 内容，建议攒到一起做完、再统一跑一次评测级正式 ingest。
3. **尚未排期/未三角分类**：issue #18（prompt/num_predict 调速）、#19（Chunker 句子边界判断评估替换为成熟分句库）、#24（超大 PDF 导致 marker 解析 OOM）、#25（极小行内排版图片被 VLM 过度解读产生幻觉）。