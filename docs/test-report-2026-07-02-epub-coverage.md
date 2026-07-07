# EPUB 内容覆盖修复 端到端审读报告

**日期：** 2026-07-02
**分支：** `feat/epub-coverage-fix`（8 个 commit）
**范围：** issue #5 修复（`ul/ol/blockquote/img` 静默丢弃）+ spine 章节号进 `page_num` + chunk_id 完整文件名 + 评审补修
**结论：** 单元测试 219 全绿；真实 EPUB 端到端人式审读通过，本次新增行为无污染；发现的 6 项质量问题全部为旧有行为，其中 1 项已修（布局表格）、1 项立项（issue #11）、4 项判定不处理

---

## 测试方式

两道独立的关：

1. **单元测试**：`pytest tests/`（排除 2 个 live 测试），覆盖 3 个 issue #5 failing test 转绿、新增 handler、兜底分支、chunk_id 格式与撞 ID 回归
2. **真实数据人式审读**：真实出版 EPUB（《The City Heiress》，Aphra Behn，1682，epubBooks 版，13 个 spine 章节）跑 解析 → Chunker → chunk 元数据 全链路，dump 后逐块直接审读，不写断言脚本、不套规则清单

## 端到端统计（布局表格修复前 → 后）

| 指标 | 修复前 | 修复后 |
|---|---|---|
| Element 总数 | 1326（text 1293 / table 20 / figure 1 / break 12） | 1326（text 1313 / table 0 / figure 1 / break 12） |
| Chunk 总数 | 134 | 105 |
| chunk_id 唯一性 | 通过 | 通过 |
| page_num 覆盖 | p0001–p0013（p0002 为无正文 spine 文档，合理缺位） | 同左 |

Chunk 数下降 29 = 20 个原子 table 碎片消失 + 相邻文本合并效应；舞台指示已自然并入正文流。

## 本次新增行为审读结果（全部干净）

- **figure 元素**：封面图产出 `![](bookcover-generated.jpg)`；路径为 **OPF 相对路径**（zip 内实际为 `OEBPS/bookcover-generated.jpg`），与 ebooklib `get_item_with_href()` 键空间一致——**约定：VLM 取图走 ebooklib，不能直接拼 zip 路径**
- **blockquote**：书信落款、舞台指示以 `> ` 前缀完整进入
- **兜底分支**：未收进 nav/TOC 等噪声
- **page_num / chunk_id**：章节定位与原书 spine 结构一一对应，新格式 `e2e/behn-city-heiress.epub/p0008/0020`

## 质量问题清单（含出现次数与处置）

| # | 问题 | 本书出现次数 | 归属 | 处置 |
|---|---|---|---|---|
| 1 | 布局表格误判为数据表格（出版社用 `<table>` 排舞台指示/歌词，自带 `epub:type="list"`、`class="simplelist"`） | **20/20**——全书 20 个 table 全部是布局表格，两个检测信号（attrs 含 list、单列无表头）各自 20/20 全覆盖 | 旧行为 | **已修**：`_is_layout_table` 启发式（epub:type/class 含 list，或单列且无 th → 降级为 text）。未采用 border 信号：真数据表格也常被 CSS 置 `border:0`，误杀风险高 |
| 2 | 诗歌/韵文行结构被空白归一化拍平 | 源文件 poem/verse 类标记 **0 个**（韵文就是裸 `<p>`），无可靠检测信号 | 旧行为 | 不处理（对 CS 教材场景无关，且无信号可修） |
| 3 | 内联标签边界空格 artifact（"Arundel , and"、"Sir Tim ."） | 105 个 chunk 中 **184 行** | 旧行为 | 不处理：消费方是 bge-m3 embedding 与 LLM 答题，对标点周围空格鲁棒，无排版需求 |
| 4 | 版权页 boilerplate 进库 | **1 页** | 旧行为 | 不处理 |
| 5 | 无标签标题被并进上一 chunk（源文件未用 `<h*>` 排献词称呼行） | **1 处** | 旧行为 | 不处理 |
| 6 | 超小 chunk（章末 flush 产物） | **1 个**（tok<15） | 旧行为 | 不处理 |

另查实：演员表 chunk 中的竖线为**源文件字面字符**（旧式转录用 `|` 模拟大括号分组，`pr04.xhtml` 中 9 处），非解析产物。

## 代码评审结果（high 档，4 findings）

| # | Finding | 判定 | 处置 |
|---|---|---|---|
| 1 | data: URI 内联图的 base64 整段进 figure content（token 炸弹） | PLAUSIBLE | **已修**：占位标记 `data-uri-image`。~~字节留在包内由 VLM 环节按需重取~~（**此表述有误，2026-07-06 勘误**：data-URI 图不是包内 item，`get_item_with_href()` 取不到，占位后字节即丢失；VLM 环节要用必须在解析 `emit_figure` 当场解码，见内嵌图片 VLM 描述回填设计 spec 第 2 节） |
| 2 | 容器裸文本节点丢失（旧）+ 内联标签经兜底产碎片元素（新副作用） | CONFIRMED | **立项 [issue #11](https://github.com/ismy-cosmos/BookAgent/issues/11)**：需改遍历模型（合并 NavigableString 与相邻 inline 标签），不搭车 |
| 3 | blockquote/li 内 `<img>` 不产 figure | CONFIRMED | **已修**：`extract_figures` 统一抽图，p/figcaption/ul/ol/blockquote 五处生效 |
| 4 | 空白归一化正则三处重复 | CONFIRMED | **已修**：提取 `_normalize_text` |

## 遗留事项

- issue #11（裸文本节点 + 碎片化）
- 旧 Chroma 库 chunk_id 格式已变（stem → 完整文件名），需重新 ingest
- 本报告审读素材为英文戏剧，中文技术书（含真数据表格、代码块、公式）的端到端审读待合入后在 full ingest 时补做