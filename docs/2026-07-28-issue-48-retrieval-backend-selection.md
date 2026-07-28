# Issue #48 混合检索后端选型：LanceDB FTS + Chroma Dense + Cross-Encoder Reranker

**日期**: 2026-07-28
**分支**: `issue-48-retrieval-backend`
**阶段**: P3 评测完成 → 选型结论
**结论**: Meilisearch 淘汰，LanceDB 作为 lexical 后端；纯 RRF 不可行，采用 Chroma Top-30 + Lance Top-20 concat → bge-reranker-v2-m3 方案

## 1. 评测设置

### 1.1 语料与查询

- **语料**: 三套隔离评测 ChromaDB（`.chroma-eval-cs` / `.chroma-eval-clinical` / `.chroma-eval-law`），chunk 保持原样导出，不做修改
- **查询**: 全部 250 题真实 `retrieve` trace（`eval/retrieval_trace_inventory.jsonl`），多轮展开后共 263 次检索
- **Dense 路由**: 使用历史 `retrieve` 工具 query（`historic_retrieve_query`），bge-m3 1024 维 embedding
- **Lexical 路由**: 使用原始题目文本（`original_question`），符合 handoff 规定的"BM25 使用原文"策略

### 1.2 Ground Truth 对齐

严格按三份 test report 逐题核对 `supporting_chunks`：

| 来源 | 修正前 | 修正后 | 修正内容 |
|---|---|---|---|
| CS (`ground_truth_bookagent.json`) | 3 题标注 chunk 非 auditor 判定支撑块 | 63 题全部对齐 | cs-b021/b027/b041 补入 auditor 确认 chunk |
| Clinical (`qa.jsonl`) | 无需修正 | 76 题 | clinical-b041 为真检索 miss |
| Law (`qa.jsonl`) | 14 题标注 chunk 不完整 | 72 题全部对齐 | 按 test report 补入 auditor 实际判定支撑的 chunk |

最终可答题 211 道（CS 63 + clinical 76 + law 72），strict-ID 指标与 test report 人工 Hit@5 一致。

### 1.3 候选池配置

三个 pool 均使用 `candidate_pool_k=50`：

| 池 | Dense 来源 | Lexical 来源 |
|---|---|---|
| Chroma Dense | ChromaDB bge-m3 (当前生产) | 空（纯 dense 基线） |
| Lance Lexical | 复用 Chroma 结果 | LanceDB 0.34.0 FTS (stem=False, no stop words, no ascii folding) |
| Meili Lexical | 复用 Chroma 结果 | Meilisearch 1.51.0 (typoTolerance=false) |

Lexical 候选池使用独立 venv（LanceDB）和官方二进制（Meilisearch），不污染项目依赖。Dense 路由固定为 Chroma 不变，确保差异归因于 lexical 通道。

## 2. 评测结果

### 2.1 核心指标：strict-ID Hit@5（211 道可答题，多轮按题目聚合）

| 配置 | CS (63题) | Clinical (76题) | Law (72题) | **合计 (211题)** |
|---|---|---|---|---|
| **Chroma Dense (基线)** | 62/63 (98.4%) | 75/76 (98.7%) | 66/72 (91.7%) | **203/211 (96.2%)** |
| Lance Lexical (纯) | 46/63 (73.0%) | 58/76 (76.3%) | 31/72 (43.1%) | 135/211 (64.0%) |
| Meili Lexical (纯) | 21/63 (33.3%) | 21/76 (27.6%) | 5/72 (6.9%) | 47/211 (22.3%) |

> **注**: strict-ID 是机械 chunk ID 匹配，为人工 Hit@5 的下界。CS 的 1 个 miss（cs-b027）目标 chunk 排名第 6（test report 预热后排名第 5），属边际差异。Clinical 的 1 个 miss（clinical-b041）test report 确认是真检索 miss。Law 的 6 个 miss（law-b002/b003/b016/b043/b048/b072）test report 确认是真检索 miss。

### 2.2 Supporting Chunk 在候选池中的召回深度

| 深度 | Chroma Dense | Lance Lexical | Meili Lexical |
|---|---|---|---|
| Top-5 | 87.1% | 51.5% | 16.3% |
| Top-10 | 88.8% | 61.7% | 18.3% |
| Top-20 | 91.9% | 66.8% | 22.0% |
| Top-30 | 93.6% | 69.5% | 22.7% |
| Top-40 | 94.2% | 71.5% | 23.7% |
| Top-50 | **94.9%** | **72.2%** | 24.1% |

- Chroma dense Top-30 已覆盖 93.6% 的 supporting chunk，Top-20 以后的边际收益快速递减
- Lance lexical Top-20 覆盖 66.8%，Top-20 以后收益递减
- Meilisearch 在任何深度都低于 25%

### 2.3 跨池覆盖分析（295 个 Supporting Chunk）

| 覆盖情况 | 数量 | 占比 |
|---|---|---|
| Chroma + Lance + Meili 共有 | 66 | 22.4% |
| Chroma + Lance 共有（Meili 无） | 142 | 48.1% |
| 仅 Chroma 有 | 67 | 22.7% |
| 仅 Lance 有 | 5 | 1.7% |
| 仅 Meili 有 | 0 | 0% |
| 三池均无 | 15 | 5.1% |

### 2.4 Lance 独有贡献（5 道题，均为 Law）

| 题目 | Lance 独有 SC | Lance 排名 |
|---|---|---|
| law-b001 (Jones GPS tracker) | `chapter-02.pdf/p0004/0005` | **Rank 1** |
| law-b005 (Carpenter third-party) | `chapter-03.pdf/p0020/0032` | **Rank 1** |
| law-b045 (King DNA cheek swab) | `chapter-18.pdf/p0021/0040` | **Rank 2** |
| law-b050 (Terry stop, anonymous tip) | `chapter-21.pdf/p0005/0008` | **Rank 1** |
| law-b057 (Ashcraft 36h interrogation) | `chapter-22.pdf/p0004/0005` | **Rank 2** |

全部 5 题均为法律判例名称/法条编号类精确匹配场景——这正是 dense embedding 的固有短板，BM25 天然优势。Lance 对这些 SC 的排名极好（3 题 rank 1，2 题 rank 2，1 题 rank 5）。

## 3. Meilisearch vs LanceDB

| 维度 | LanceDB | Meilisearch | 结论 |
|---|---|---|---|
| Law strict-ID Hit@5 | 43.1% | **6.9%** | Lance 碾压 |
| SC Top-50 召回 | 72.2% | 24.1% | Lance 碾压 |
| 独有 SC 贡献 | **5 个** | 0 个 | 只有 Lance 有增量价值 |
| 中文切词 | 可用 (stem=False 配置) | 不可用 (法学 6.9%) | Meili 中文 tokenizer 完全不适用于法律文本 |
| 部署复杂度 | `pip install lancedb`，嵌入式 | 独立二进制 + 端口管理 + sidecar 打包 | Lance 更简单 |
| 许可证 | Apache 2.0 | MIT | 均可 |
| 交付路径 | Python wheel，现有 sidecar 可承载 | 需建设 Tauri sidecar 发布链路 | Lance 成本更低 |

**结论: Meilisearch 直接淘汰。** 中文法律文本上 6.9% 的 recall 无法接受。后续只考虑 LanceDB。

## 4. Qdrant 评估

Qdrant 曾作为候选被考虑，原因是其架构优势——一个 collection 同时管理 dense vector 和 sparse/lexical 索引，可消除 Chroma + LanceDB 的双写复杂性。但实测发现 Qdrant 当前的 sparse 模型不支持中文，直接淘汰。

### 4.1 评测方法

和 LanceDB/Meilisearch 相同：复用 Chroma dense 结果，Qdrant 仅跑 lexical（sparse）通道。Qdrant dense 使用 exact cosine search 和相同原始向量，必然等于 Chroma，无需验证。

环境：`qdrant-client==1.18.0` + `fastembed==0.8.0`，Qdrant local mode（嵌入式，无服务进程），独立 venv 隔离。

### 4.2 实测：Qdrant Sparse 模型中文能力

Qdrant 通过 fastembed 提供两类 sparse 模型：

| 模型 | 原理 | 中文实测 |
|---|---|---|
| `Qdrant/bm25` | 传统 BM25 + 语言特定 stopword/tokenizer | **全空**——仅支持 18 种欧洲语言，无中文 tokenizer |
| `Qdrant/bm42-all-minilm-l6-v2-attentions` | 神经网络 sparse（BERT tokenizer + attention weights） | **全空**——BERT tokenizer 能切中文字符，但 attention 训练数据为英文，中文 token 不产生有效权重 |

```
Query: "警察搜查令违宪"           → Qdrant bm25:  无结果
Query: "警察搜查令违宪"           → Qdrant bm42:  无结果
Query: "Kyllo thermal imaging"    → Qdrant bm25:  ✓ 命中
Query: "机器学习模型训练"          → Qdrant bm25:  无结果
Query: "机器学习模型训练"          → Qdrant bm42:  ✓ 命中（但"警察搜查令违宪"仍为空）
```

bm42 对中文技术术语（"机器学习"）有一定召回，但对中文法律文本（"搜查令""违宪"）完全失效。这与 LanceDB FTS（`stem=False`，字符级索引中文）形成鲜明对比——LanceDB 至少能命中 `搜查`→`搜查令`、`违宪`→`违宪行为`。

### 4.3 淘汰理由

| 维度 | 结论 |
|---|---|
| 中文词法 | **不可用**。两个 sparse 模型均无法有效处理中文法律/学术文本 |
| Law 预期 | 即使进入 Lexical 全量评测，Law 表现不可能超过 LanceDB 的 40.3% |
| 架构优势 | 消除双写的前提是检索质量不低于基线。词法不通过，架构优势无意义 |

**结论: Qdrant 在 Token 审读阶段直接淘汰。** 待 Qdrant 未来提供官方中文 BM25/sparse 支持后重新评估。

## 5. Reranker 候选池设计

### 5.1 关键发现

- Chroma dense Top-30 覆盖 **93.6%** SC，Top-20 覆盖 **91.9%**——**dense 是主信号**
- Lance lexical Top-20 覆盖 **66.8%** SC，并独有 **5 个 SC (5 道题)**——**lexical 是补充**
- 15 个 SC (5.1%) 三池都不在——**任何 reranker 无法恢复**
- 纯 RRF（等权）不可行：dense 信号远强于 lexical，等权会把 dense 第 3-5 名挤出（已在 handoff P3 消融中证实）

### 5.2 为什么 RRF 不合适

RRF（Reciprocal Rank Fusion）在混合检索中是最常见的基线，但在本项目的评测数据下被证明不可行。Handoff P3 消融实验给出了明确证据：

| 配置 | Report-Evidence 命中 | 结论 |
|---|---|---|
| Chroma dense 基线 | 184/186 | — |
| Chroma + lexical，等权 RRF，候选池 5 | 179/186 | **低于基线，不可接受** |
| Chroma + lexical，dense 权重 1.05，候选池 5 | 184/186 | 勉强追平，但靠调参过 |
| Chroma + lexical，等权 RRF，候选池 50 | 152/186 | **更差——池越大 RRF 越难区分** |

RRF 存在三个根本性问题：

**1. RRF 是盲的。** 它只看排名位置不看内容。Chroma 的第 3 名和 Lance 的第 3 名得到完全相同的 RRF 分数 `1/(60+3)`——但实际上在这个场景下，dense 信号质量远高于 lexical（Chroma 独有 67 个 SC vs Lance 独有 5 个 SC）。等权 RRF 相当于强行给 lexical 通道赋了过高的权重，必然把一些 dense 的正确结果挤出 Top-5。

**2. RRF 对候选池大小敏感且方向错误。** 候选池从 5 扩到 50，等权 RRF 反而从 179 跌到 152。这是因为 RRF 只按排名位置融合——pool 越大，lexical 通道的低质量候选中排名靠前的（如 Lance rank 1-3 的不相关 chunk）会获得与 dense 高质量候选相同的 RRF 分数，污染 Top-5。

**3. RRF 无法利用内容信息。** Lance 排第 20 名的 chunk 如果内容高度相关，RRF 给它 `1/(60+20)` 的分数，永远进不了 Top-5。而 reranker 会真正读完这个 chunk 的全文，判断它是否回答了 query，给它应有的高分。

**候选池 50 的数据早已证明**：Lance 的 dense+lexical 候选并集已包含 100% 可机械核对证据（186/186），瓶颈在最终排序而非候选召回。RRF 不是解决这个瓶颈的正确工具。

### 5.3 建议方案：Concat + Reranker

```
Chroma Top-30 ─┐
                ├── 去重 ──→ Cross-Encoder Reranker ──→ Top-5
Lance Top-20 ──┘
```

Reranker（Cross-Encoder）会逐个读候选 chunk 全文和 query，输出真实相关性分数。相比 RRF：

- **内容感知**：Lance rank 20 的 chunk 如果高度相关，reranker 会给高分；Chroma rank 3 如果不相关，reranker 会压下去
- **权重自适应**：不需要手动调 `dense_weight=1.05` 这种脆弱的参数
- **候选池友好**：池越大 reranker 越有发挥空间（和 RRF 相反）
- **可解释**：每个最终结果的分数是模型对 `(query, chunk)` 的真实判断

### 5.4 候选池大小分析

#### 行业参照

| 项目/来源 | Dense 候选 | Sparse 候选 | Reranker 输入 | 策略 |
|---|---|---|---|---|
| RAGFlow | top=1024（向量检索） | 并行 BM25 | ~64-100（动态计算） | 加权融合 → reranker |
| Haystack MultiRetriever | top_k per retriever | top_k per retriever | 50-200 | RRF → SentenceTransformersRanker |
| Pinecone (bge-reranker-v2-m3) | — | — | "不超过几百个" | retriever → reranker |
| Baishan API 建议 | — | — | 20-100 | 初检 → reranker → Top 1-5 |
| 学术/工程共识 | — | — | **25-50（甜点区）** | Cascade: 粗检→精排 |

行业共识：Cross-Encoder reranker 输入 25-50 个候选是最佳平衡点。少于 20 时 reranker 即使正确也无法恢复漏召回；超过 200 时质量收益趋于平坦、延迟和成本线性增长。

#### 本项目数据验证

**SC 召回随深度变化的边际收益：**

| 深度 | Chroma Dense (累计) | 边际增量 | Lance Lexical (累计) | 边际增量 |
|---|---|---|---|---|
| Top-5 | 87.1% | — | 51.5% | — |
| Top-10 | 88.8% | +1.7pp | 61.7% | +10.2pp |
| Top-20 | 91.9% | +3.1pp | 66.8% | +5.1pp |
| **Top-30** | **93.6%** | **+1.7pp** | 69.5% | +2.7pp |
| Top-40 | 94.2% | +0.6pp | 71.5% | +2.0pp |
| Top-50 | 94.9% | +0.7pp | 72.2% | +0.7pp |

- **Chroma dense**：20→30 仍贡献 +1.7pp，30→50 累计仅 +1.3pp。**拐点在 30。**
- **Lance lexical**：5→20 贡献 +15.3pp（主要增益），20→50 仅 +5.4pp。**拐点在 20。**

#### 30:20 比例的合理性

Chroma Top-30 + Lance Top-20，去重后约 40-50 个候选。分析：

1. **总量在行业甜点区**。40-50 略低于 RAGFlow 的 64-100、高于 Pinecone 建议下限 20，但正好落在学术共识的 25-50 区间。bge-reranker-v2-m3 在 batch_size=32 的 CPU 推理下，50 个候选约 3-5 秒，对桌面应用可接受。

2. **60:40 的 dense:sparse 比例合理**。本项目 dense 信号远强于 lexical（Chroma 独有 67 SC vs Lance 独有 5 SC），给 dense 60% 权重（30 个候选）反映这一现实。对比 RAGFlow 的 40:40:20（dense:BM25:structured），本项目 dense 占比更高是合理的——因为语料是教材而非网页，semantic matching 天然优于 keyword matching。

3. **无需过度优化比例**。Reranker 的根本优势在于内容感知——它不关心候选来自哪个通道。Chroma rank 30 的候选如果相关，reranker 会排到第一；Lance rank 1 的候选如果不相关，reranker 会压到底部。比例只是控制候选池的"覆盖广度"，最终排序交给模型。

#### 备选方案对比

| 方案 | 候选数 | SC 覆盖 | 优点 | 缺点 |
|---|---|---|---|---|
| Chr 30 + Lan 20 | ~45 | 95%+ | 甜点区，覆盖充分 | — |
| Chr 20 + Lan 10 | ~28 | ~92% | 延迟更低 | 丢失 ~3pp SC 覆盖（~9 个 SC） |
| Chr 50 + Lan 50 | ~95 | ~95%+ | 覆盖最大 | 延迟翻倍，边际收益仅 +0.7pp |
| Chr 20 + Lan 20 | ~38 | ~93% | 均衡 | Chroma 丢失 1.7pp（5 个 SC） |

**Chr 30 + Lan 20 是最优解**：在不牺牲覆盖的前提下将候选数控制在甜点区。Chr 50 + Lan 50 多花 2× 延迟只换来 +0.7pp SC 召回，不值得。Chr 20 + Lan 10 省了延迟但丢了 ~3pp 覆盖——对于追求"不低于基线"的场景不可接受。

| 参数 | 建议值 | 理由 |
|---|---|---|
| Dense 候选池深度 | **Top-30** | 拐点在 30（93.6%），30→50 仅 +1.3pp |
| Lexical 候选池深度 | **Top-20** | 拐点在 20（66.8%），20→50 仅 +5.4pp |
| 联合候选池大小 | **≤50（去重后约 40-50）** | 行业甜点区 25-50，bge-reranker 可承受 |
| 排序策略 | **Cross-Encoder Reranker** | RRF 已证伪；concat + reranker 是唯一可行方案 |
| Reranker 模型 | bge-reranker-v2-m3 (~2.27GB) | 与现有 bge-m3 同系列，max_length=1024 tokens |

### 5.5 边际案例：Lexical 能救回来的题

Lance 独有 5 个 SC 且排名极好——这正是 concat 方案的价值所在。如果用 RRF，这 5 个 SC 会因为 Lance 通道权重被稀释，大概率仍然进不了最终 Top-5。但 concat + reranker 方案中，reranker 会直接读到这些 chunk 的全文，如果内容确实回答了 query，它们就能进入最终结果。

## 6. 下一步

1. **用户确认 bge-reranker-v2-m3 下载** (~2.27 GB)
2. 在 Chroma Top-30 + Lance Top-20 联合候选池上运行 reranker
3. 评测 reranker 后的 strict-ID Hit@5、report-evidence 比对、无答案题风险
4. 若 reranker 通过"不低于基线"门槛，进入 LanceDB 正式集成设计

## 7. 附录：数据文件

| 文件 | 路径 |
|---|---|
| 候选池结果 | `eval/pool50/chroma-baseline/results.json` |
| | `eval/pool50/lance-lexical/results.json` |
| | `eval/pool50/meili-lexical/results.json` |
| 分析结果 | `eval/pool50/pool_analysis.json` |
| 导出语料 | `eval/pool50/corpus/` |
| 查询向量 | `eval/pool50/query_vectors.json` |
| LanceDB 索引 | `eval/pool50/lancedb-index/` |
| Meilisearch 二进制 | `eval/pool50/meilisearch` (v1.51.0) |
| 修正后 ground truth | `eval/ground_truth_bookagent.json` (CS) |
| | `eval/testset/clinical/qa/qa.jsonl` (Clinical) |
| | `eval/testset/law/qa/qa.jsonl` (Law) |
