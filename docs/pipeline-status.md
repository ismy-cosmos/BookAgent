# 核心管线状态与待办优先级

追踪主干链路 解析 → 分块 → 元数据 → 入向量库 → 检索召回 的实时状态，以及下一步该修哪个 issue。随代码推进持续更新，不是一次性快照。

## 各阶段状态

- **解析 → 分块 → 元数据**：已完成。
- **入向量库**：写库代码真实存在（`ChromaStore.add_chunks` / `scripts/ingest.py`），非 stub，但从未用真实数据端到端跑通过——磁盘上此前不存在任何 `.chroma` 持久化数据，PR #4 的测试全部基于 mock。
- **检索召回**：此前 agent 的 `retrieve` 工具接的是 `StubExecutor`，返回硬编码假 chunk，完全不碰 `ChromaStore`/`Embedder`。正在 `feat/realexecutor-retrieval` 分支上接入真实检索（`RealExecutor`），设计与计划见 `docs/superpowers/specs/2026-07-03-realexecutor-retrieval-landing-design.md` 与对应 plan（该目录已 gitignore，仅存于本地）。

## 待办 issue 优先级顺序

1. **进行中：RealExecutor 检索落地**（`feat/realexecutor-retrieval` 分支）。让"检索召回"这一端第一次接上真实数据，是主干链路能否端到端闭环的关键缺口。
2. **下一步：issue #6**（`scripts/ingest.py` 核心编排逻辑零测试覆盖，批量处理无单文件失败容错）。这是关键路径——要可靠地把真实书批量灌进向量库，必须先有这层容错，否则一批文件里一个坏 PDF/WhisperX 崩/Ollama 连不上就会中断整批。
3. **之后：issue #13 + #11 + #10 攒成一批一起做**：
   - #13：内嵌复杂 atomic（图/表/公式）未路由给 VLM 理解。
   - #11：EPUB 容器直接子级裸文本节点丢失，内联标签经兜底分支产生碎片元素。
   - #10：`audio.py` WhisperX 短 VAD segment 直接成 chunk，未走 chunker 打包逻辑。
   - 这三者都会改变最终入库的 chunk 内容，攒齐一起做完、再统一跑一次评测级正式 ingest，避免中途多次重灌向量库。