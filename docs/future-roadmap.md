# 后续独立项路线图

记录明确排在当前里程碑之后、尚无实现计划的独立工作项。每项列出背景依据和现有铺垫，避免下次拾起时重新讨论一遍。

## TypeScript `ask_questions` 前端

`RealExecutor` 落地时（`feat/realexecutor-retrieval` 分支）已经决定本次纯 Python 打底，前端拆成下一个独立子项目。

- 已打好的接缝：`pipeline/agent/answer.py` 的 `answer()` 无状态入口 + `AnswerResult`/`ChatTurn`/`Citation` dataclass。
- 下一步第一件事：把 `answer()` 包成 HTTP 端点——HTTP 契约要跟前端一起定，不在后端单方面先定死。
- 范围提醒：官方任务书对交互的硬性要求只是"一键对话启动"，CLI（`scripts/ask_cli.py`）已经满足。GUI 前端对应评审维度里的"产品思维/用户体验闭环"，是加分项，不是必需交付物——排期时不要让它挤占被打分的核心管线与评测。

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