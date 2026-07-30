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

**已完成（续2）**：**issue #49**（真实根因是marker把TIP/CRUX/ASIDE侧边栏框误判成`#`标题，触发flush截断续接句子——8本真实书人工审查27处误判、24处被关键词规则覆盖，另加WARNING/CAUTION/SIDEBAR共6词，PR #53，2026-07-17合并，真实cpu-intro.pdf端到端验证过）。issue #19评论区那条"跨页断句丢失"的原始发现已经被#49解决，#19本身保留的"要不要换分句库"范围仍暂缓。

**已完成（续3）**：**CS测试集全量真实审查+扩容至76题**（PR #55，2026-07-20合并）——用真实端到端管线（`book_id=cs-eval`）逐题核验原60题，改判2道question_type、订正2道ground truth（`derive_ground_truth.py`不检查`question_type`导致的脚本bug）；扩容16题（cs-b056~071，覆盖已有PDF补充无答案题、`java-ch1-e2e.epub`新增10题、图片新增3题）；排查并重出9道用了元提问模板/元指代开头的题目。核心指标：Hit@5=98.4%、工具调用率=100%、幻觉率=7.9%全量口径/46.2%无答案题专项口径。详细逐题记录见`docs/test-report-2026-07-20-cs-testset-audit.md`，是issue #40设计阶段的证据基础。审查过程中发现calculate工具在特定英文措辞下会反复触发`_ALLOWED_NODES`白名单拒绝、模型不会调整策略导致`MAX_ROUNDS_EXCEEDED`完全无输出，已拆分为独立 **issue #54**（方案：扩展`_ALLOWED_NODES`支持位移运算+窄口子白名单函数，不引入新依赖，不属于#40范畴）。

**已完成（续4）**：**issue #24**（超大PDF一次性解析导致OOM killer杀进程，PR #57，2026-07-22合并）——`MarkerParser` 解析前用pypdfium2读页数，超过阈值（默认100页）的文件物理切分成临时小PDF逐份解析、按绝对页码拼接，`Chunker`零改动；顺带修复真实数据发现的独立bug（marker默认分页分隔符跟宽表格表头分隔行碰撞导致页码系统性漂移，`threads-intro.pdf`真实案例）；批次级暂停语义同`AudioParsePaused`（当前文件已解析批次全部作废，不影响其他文件）。真实大文件验证：《Criminal Procedure》915页批大小100完整跑通无OOM。**排查过程中发现《Nursing Pharmacology》本身存在系统性表格解析质量问题**（Pressbooks平台导出通病，多处药物表格被误判成散乱文本，非本次修复范围），已放弃该书作为临床学科基准语料，改选 OpenStax《Pharmacology for Nurses》4章节（130页，已实测解析质量可靠），详见`eval/parser_selection/textbook-candidates.md`。**PR合并后2026-07-22真实使用中发现新的独立问题**：一是pdftext库默认并行文本抽取（`pdftext_workers=4`）在CUDA已加载的进程里用fork/forkserver起子进程会挂起，已修复（`pdftext_workers=1`，marker自己CLI也用同样方式规避过这个问题）；二是marker/pdftext内部对pypdfium2的调用在长驻后端进程里处理累积页数过多后会SIGSEGV崩溃（原生层，第三方库范围，非本项目代码问题），已开**issue #59**跟踪，考虑方向是进程级定期回收（类似Gunicorn worker recycling），需要新加Tauri侧中途重启能力，未实现 → **2026-07-30 已实施 Python 侧 worker 进程隔离方案（issue #59）**。

**已完成（续5）**：**issue #59**（marker/pypdfium2 累积页数 SIGSEGV，2026-07-30 实施）——marker 解析迁入可回收 worker 子进程（`pipeline/parse/marker_worker.py` + `marker_worker_client.py`），NDJSON 协议通信，默认页数预算 200 页自动回收，崩溃只杀 worker 不杀后端、重试自愈。`MARKER_WORKER_DISABLED=1` env 可回退进程内路径。详见 `docs/superpowers/specs/2026-07-30-issue59-marker-worker-isolation-design.md`。670 测试全绿，无回归。

1. **下一步：临床/法学学科测试集构建**（2026-07-21 决策，排在消融之前）——候选书目已定（《Nursing Pharmacology》/《Criminal Procedure》），用当前管线 ingest + 按 CS 76 题方法论出题 + 页码级 GT 核验。先于消融的理由：消融矩阵要调的旋钮全是领域敏感的（#48 BM25 的关键词信号在法律/临床语料里才密集、#40 阈值的 cosine 距离分布随领域漂移），只在 CS 上调参必留返工债；而测试集的耐久资产（出题+页码级 GT）不随 chunker 改动失效，重跑评测有现成脚本，先建的返工成本低。
2. **之后：三学科消融矩阵**——#40 相关性阈值 + #48 混合检索（BM25+向量）+ rerank 精排 + chunk 结构化，在 CS+临床+法学三套语料上统一做，检索层参数一次定型。
3. **之后：场景功能+场景测试集**——跨源核对/参数化结构化抽取/calculate 财务健壮性，实现设计已定稿（`docs/superpowers/specs/2026-07-21-scenario-features-design.md`）；场景定位依据 2026-07-21 三簇真实工具生态调研（`docs/product-positioning.md`：锚定法律案件准备+小型 M&A 尽调，临床退出场景叙事降为学科基准）。
4. **issue #11 暂缓**（EPUB 容器直接子级裸文本节点丢失）：用真实语料核实过，当前EPUB测试语料（`java-ch1-e2e.epub`）里这个具体bug模式命中0次，是理论缺陷不是已验证的真实问题（跟#19一个性质）。等测试集扩充过程中如果真的撞见这个问题，再回来处理，不主动排期。
5. **尚未排期**：issue #25（极小行内排版图片被 VLM 过度解读产生幻觉，同批 CS 评测发现，图片理解层问题）、#19（Chunker 句子边界判断评估替换为成熟分句库，issue 原文已注明"暂缓"）、**#54**（calculate工具表达式沙箱不支持位移运算，特定英文措辞下模型死循环触发`MAX_ROUNDS_EXCEEDED`，方案已明确，独立于#40，可随时排期；2026-07-21 补充了财务场景失败类别，修复方案并入场景功能 spec）、**#56**（AudioParser 无说话人分离，多人录音无法归属说话人，2026-07-21 新提，决定跨源核对的粒度上限）、**#59**（marker/pypdfium2 累积页数 SIGSEGV，2026-07-22 新提 → 2026-07-30 已实施 worker 进程隔离方案，见下方"已完成（续5）"）。

## 里程碑覆盖度缺口

README 目标指标要求 Hit@5 覆盖 **CS / 临床医学 / 法学** 三学科，目前只有 **CS 完整跑完**（`eval/testset/cs/`，76 题 QA + 真实评测，PR #41 首轮60题 → PR #55 全量审查+扩容至76题）。法学（《Criminal Procedure》，CALI eLangdell，915页，`eval/testset/law/raw/book/`）、临床（《Pharmacology for Nurses》OpenStax选4章节，130页+配套音频80.6分钟，`eval/testset/clinical/raw/book/`+`raw/audio/`，2026-07-21/22 因原选定的《Nursing Pharmacology》表格解析质量问题重新选型，详见`eval/parser_selection/textbook-candidates.md`）两个学科语料均已就位（issue #24 大文件OOM修复后可正常ingest），但 ingest/QA 出题/评测三步均未开始。**2026-07-21 已决策：现在启动，排在消融矩阵之前**（理由见上方待办第 1 条）。