# 核心管线状态与待办优先级

追踪主干链路 解析 → 分块 → 元数据 → 入向量库 → 检索召回 的实时状态，以及下一步该修哪个 issue。随代码推进持续更新，不是一次性快照。

## 各阶段状态

- **解析 → 分块 → 元数据**：已完成。
- **入向量库**：写库代码（`ChromaStore.add_chunks` / `scripts/ingest.py`）已用真实数据端到端验证过；批量多文件场景下的单文件失败容错+回滚+连续失败熔断已完成（PR #23）；三阶段架构（解析→VLM批量描述→入库，PR #26）已合并，整本书级别的正式 ingest 链路完整打通。入口脚本级强制离线模式（`HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`，覆盖 embedder/marker/whisperx）已合并（PR #43-45），避免 HuggingFace 服务故障拖垮本地入库流程。
- **检索召回**：`RealExecutor` 已落地（PR #15，`feat/realexecutor-retrieval` 分支），`retrieve`/`get_chunk` 走真实 `ChromaStore`/`Embedder`，不再是 `StubExecutor` 硬编码假数据。
- **VLM/Ollama 调用方式**：`VLMImageParser`/`check_vision.py` 已统一改用 `openai` SDK（PR #21），修掉了顺带发现的 VRAM 判断阈值过时问题，`VLMImageParser` 用完模型会主动释放显存，避免跟 embedder 抢 GPU。
- **AudioParser**：已改用项目自己独立的 `whisperx.venv` + Python API wrapper（PR #22），不再依赖 `BookAgent-Baseline` 仓库路径。
- **内嵌图片 VLM 描述回填**：已完成并合并（PR #26，`feat/vlm-figure-routing`）——PDF/EPUB 内嵌图与独立图片文件统一在 ingest 的 VLM 批量阶段生成描述回填 chunk 正文，发送前 resize（长边 2048px 上限，真实 GPU 实测防显存溢出），单图失败降级、连续失败熔断（默认 3 张、跨批次计数）。真实数据端到端审读见`docs/test-report-2026-07-06-vlm-figure-routing.md`：40张图100%成功、真实token消耗45286（均1132/图），发现两项质量问题（caption重复、极小图片幻觉，见issue #25）留待后续处理，不阻塞。

## 待办 issue 优先级顺序

**已完成**：issue #6（`scripts/ingest.py` 批量单文件失败容错+回滚+连续失败熔断，PR #23）、issue #16（8GB 显卡 mmproj 上不了 GPU 是 Ollama 自身回归 bug，已升级版本修复）、**issue #13 + #14**（内嵌图片 VLM 描述回填 + resize，PR #26，2026-07-07 合并）、**issue #20**（GPU 显存互斥锁：`ImportQueue` 单工作线程 FIFO 队列+忙碌状态接入问答/删除接口，PR #28，2026-07-08 合并，issue 已关闭）、**issue #27**（ingest 异步执行+进度上报：`run_ingest()` 可复用化+解析/VLM双缓存+暂停支持（PR #29）、`ImportQueue` 真实接入+待导入文件列表+进度/暂停/取消 HTTP 接口（PR #30），2026-07-09 全部合并，issue 已关闭）、**issue #34**（`book_id` 短于 3 字符时 ChromaDB 拒绝创建 collection，2026-07-14 关闭）、**issue #18**（VLM prompt 改简洁版+temperature=0，端到端提速近1倍 13.0→23.7页/分钟，PR #41，2026-07-16 关闭）、**issue #36**（忙碌锁改双向互斥+导入前释放 Ollama 驻留模型，PR #39，2026-07-16 关闭）。

CS 学科 60 题真实问答评测（PR #41）跑完后，新增 **issue #40**（retrieve 无相关性阈值，跨章节内容被误归因产生幻觉），与 #17 同属引用溯源可靠性问题。

**已完成（续）**：**issue #17**（混合计算+书本知识复合题 retrieve 被跳过，system prompt 加 few-shot 示例修复，真实模型验证3个场景，PR #50，2026-07-17 合并；同批顺带修复2处chunk质量bug：冒号前缀继承重复内容、CAPTION_RE 不认中文"图/表"caption）、**issue #10**（audio.py 短 VAD segment 未走打包逻辑，新增 `pack_audio_segments()` 贪心打包到256 token，PR #52，2026-07-17 合并，真实音频数据端到端验证过）。

排查真实chunk数据分布时新发现两项：**issue #49**（chunker跨页断句：flush条件卡在断点和续接内容之间时没有补救机制，从 #19 评论区拆分独立）、**issue #48**（检索层纯dense向量检索缺关键词精确匹配，建议评估混合检索BM25+向量）。

1. **下一步：issue #11 + #49**：
   - #11：EPUB 容器直接子级裸文本节点丢失，内联标签经兜底分支产生碎片元素。
   - #49：chunker 跨页断句丢失，flush 条件截胡续接内容时无补救。
   - 都会改变最终入库的 chunk 内容，建议攒到一起做完、再统一跑一次评测级正式 ingest 对比 #40 修复效果。
2. **同一批可评估：issue #48**（混合检索 BM25+向量），跟 reranker/#40 阈值机制同一批规划，见 `docs/product-positioning.md`。
3. **尚未排期**：issue #25（极小行内排版图片被 VLM 过度解读产生幻觉，同批 CS 评测发现，图片理解层问题）、#24（超大 PDF 导致 marker 解析 OOM，当前语料未触发）、#19（Chunker 句子边界判断评估替换为成熟分句库，issue 原文已注明"暂缓"）。

## 里程碑覆盖度缺口

README 目标指标要求 Hit@5 覆盖 **CS / 临床医学 / 法学** 三学科，目前只有 **CS 完整跑完**（`eval/testset/cs/`，60 题 QA + 真实评测，PR #41）。临床医学（候选书目已定：《Nursing Pharmacology》）、法学（候选书目已定：《Criminal Procedure》，CALI eLangdell）两个学科候选书目早已选定（`eval/parser_selection/textbook-candidates.md`），但 ingest/QA 出题/评测三步均未开始，`eval/testset/clinical/`、`eval/testset/law/` 目前只有占位目录。是否现在启动、还是等上面 issue 修完再复制到新学科，待决策。