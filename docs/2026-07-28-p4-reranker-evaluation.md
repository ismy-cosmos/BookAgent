# P4 Reranker 评测报告：bge-reranker-v2-m3 未能超越 Dense 基线

**日期**: 2026-07-28
**分支**: `issue-48-retrieval-backend`
**状态**: P4 评测完成 → Reranker 不通过验收

## 1. 评测目标

验证 Concat + Reranker（Chroma Dense Top-30 + Lance Lexical Top-20 → bge-reranker-v2-m3 → Top-5）能否达到或超过 Chroma Dense 基线（203/211, 96.2%）。

## 2. 评测路径

在进入 Reranker 评测前，先完成了两项前置工作：

### 2.1 修复 LanceDB 中文分词

LanceDB 底层 Tantivy 使用 `simple` tokenizer，按空格/标点分词。中文没有空格，整段中文被当作单一 token，导致 FTS 对中国查询完全失效。

**实测**：
```
'搜查令'       → 0 results  (simple tokenizer: 中文是 giant token)
'Fourth Amendment' → 3 results  (simple tokenizer: 英文正常分词)
```

中文查询 3/41 (7.3%)，英文查询 26/46 (56.5%)。旧的 Lance Law 43.1% 是英语题目比例高拉高的假象。

### 2.2 实现语言感知 Lexical 检索

参照 TREC 2024 NeuCLIR（Query Translation + BM25）和 Azure AI Search（多语言字段 + searchFields 路由）的架构：

**索引侧**：
- Chunk 级语言检测（`has_cjk` → zh / en）
- `content_lex_en`：英文 chunk 原文，走 simple tokenizer
- `content_lex_zh`：中文 chunk 经 Jieba 预分词（`" ".join(jieba.cut(text))`），走 simple tokenizer

**查询侧**：
- 查询语言检测 → 同语言路由到对应字段
- 跨语言：Argos Translate + 术语保护层翻译查询 → 查另一字段
- 术语字典（60 个领域词）用占位符机制在翻译前后保护专业术语

**效果**：

| 方案 | Lexical Hit@5 |
|---|---|
| Old Lance (broken zh) | 133/213 (62.4%) |
| Jieba only (no routing) | 125/213 (58.7%) |
| **Lang-aware + translation** | **168/213 (78.9%)** |

| Subject | Old Lance | Lang-aware |
|---|---|---|
| CS | 45/63 | **51/63** |
| Clinical | 59/77 | **68/77** |
| Law | 29/73 | **49/73** |

Jieba 预分词修复中文 BM25；语言路由消除 jieba 对英文技术标识符的破坏（如 `pthread_join` → `pthread _ join`）。

## 3. Reranker 评测结果

### 3.1 主结果

| Subject | Baseline (Dense) | Reranker (Concat) | Δ |
|---|---|---|---|
| CS | 62/63 (98.4%) | 60/63 (95.2%) | -2 |
| Clinical | 75/76 (98.7%) | 74/76 (97.4%) | -1 |
| Law | 66/72 (91.7%) | 58/72 (80.6%) | -8 |
| **Total** | **203/211 (96.2%)** | **192/211 (91.0%)** | **-11 (-5.2%)** |

Reranker 在所有三个科目上均未超过基线。Law 退化最严重（-8/72）。

### 3.2 CS/Clinical 退化：纯 Dense 池同样退化

CS 和 clinical 的 Reranker 评测**未混入任何 Lance 候选**（Lexical 通道仅对 Law 开放）。Reranker 仅对 Chroma Top-30 重排：

| Subject | 候选池 | Baseline | Reranker |
|---|---|---|---|
| CS | Chroma Top-30 only | 62/63 | 60/63 (-2) |
| Clinical | Chroma Top-30 only | 75/76 | 74/76 (-1) |

**结论：Reranker 在不引入任何 BM25/Lance 噪声的情况下仍然退化。** 问题不在候选池质量，在 Reranker 本身的排序能力。

### 3.3 Law 退化：Lance 噪声 + Reranker 排序双重因素

9 个 Law lost 案例分类：

| 类别 | 数量 | 说明 |
|---|---|---|
| Reranker 内容偏好 | 4 | GT 是规则/定义文本，Reranker 偏好异议意见、引用文本、庭审开场白 |
| Lance 噪声干扰 | 5 | Lance 候选进入 Top-5，无一提供独特价值 |

### 3.4 退化案例分析

**cs-b049**（分段地址翻译）：GT 是 base-and-bounds 伪代码算法（dense rank 2）。Reranker 偏好同一章中带具体数值示例的描述性段落。

**cs-b050**（分段碎片）：GT 定义外部碎片问题（dense rank 2）。Reranker 偏好同一章中讲解决方案（best-fit/worst-fit 算法）的段落——偏好方案描述而非问题定义。

**clinical-b042**（丙戊酸儿童剂量）：GT 是纯文本剂量说明（dense rank 1）。Reranker 偏好药品-途径-剂量表格的标题行——偏好结构化数据。

**law-b001**（Katz 合理隐私期待）：GT 是 Katz 案 holding（dense rank 1）。Reranker 偏好异议法官意见（"The Court argues—and I agree—"）——偏好修辞性文本。

**law-b053, law-b080**（J.D.B. v. North Carolina，Miranda 未成年人）：GT 是实质辩论问答。Reranker 偏好庭审开场白（"We'll hear argument next..."）——偏好程序性文本。

### 3.5 Query 拼接策略消融

对比了三种 query 构造方式：

| Query 策略 | 效果 |
|---|---|
| concat(lexical_query, dense_query) | GT rank 6-10 ✗（query 过长，信息稀释） |
| dense_query only | GT rank 1-2 ✓ |
| lexical_query only | GT rank 1-4 ✓ |

拼接两个 query 导致文本过长，Reranker 被细节噪声带偏。最终采用 dense_query only。

## 4. 为什么 Reranker 退化：研究佐证

### 4.1 Databricks "Drowning in Documents" (2024)

直接证实了我们的发现：

> "Rerankers frequently performed **worse than standalone retrievers (bi-encoders)** , often assigning high scores to documents with **no lexical or semantic overlap** with the query."

三个根因：
1. **训练负样本少**：Reranker 训练时只看到 ~4 个负样本，而 embedding 模型看到 ~16384 个。Reranker 只在与其有限训练分布相似的文档上表现最佳。
2. **Pointwise 评分**：独立给每对 (query, doc) 打分，无法比较文档间差异。Listwise 更鲁棒。
3. **领域不匹配**：MS MARCO 训练的通用 Reranker 面对法律/医学/CS 教材时不稳定。"每个额外文档都增加了模型给不相关文档打高分的风险。"

### 4.2 EMNLP 2025: Positional Bias 研究

> "Strong retrievers systematically bring highly distracting passages to top ranks (over 60% of queries have at least one highly distracting passage in top-10)."

基线已经很好的情况下（96.2%），Top-K 候选池中充满高质量但"不完全对"的干扰段落。Reranker 无法区分这些微妙的差异。

### 4.3 社区实践规则

中文技术评测建议：**"如果第一阶段 recall@50 < 0.85，先别加 Reranker"**。我们的情况相反——recall 94.9% 已在天花板，Reranker 没有改善空间。

社区共识的 reranker 失效场景：
- 基线检索已接近完美（我们的情况：96.2%）
- 领域不匹配（MS MARCO vs 法律/医学/CS 教材）
- 候选池中存在大量高度相关但不精确匹配的干扰项

## 5. 结论

### 5.1 Reranker 验收：不通过

bge-reranker-v2-m3 在 strict-ID Hit@5 上未能达到 Chroma Dense 基线（192/211 vs 203/211）。即使不引入任何 lexical 候选，纯 Dense Top-30 经过 Reranker 后仍然退化。

### 5.2 Language-Aware Lexical：随时可用

语言感知的 LanceDB FTS（Jieba 预分词 + 语言路由 + Argos Translate 翻译 + 术语保护）将 Lexical Hit@5 从 62.4% 提升至 78.9%（+35 题）。中文 BM25 真正可用但是目前不适配项目。

### 5.3 推荐架构

基于所有评测数据，推荐的检索架构为：

```
Chroma Dense (bge-m3) Top-5 → 直接返回
  96.2% Hit@5，目前最优

LanceDB Lang-Aware Lexical → 作为补充通道
  78.9% Hit@5，对法律案名/法条号等精确 token 场景有价值

不推荐使用 Reranker
  在本数据集上无法超越 Dense 基线
```

### 5.4 可能的改进方向（未验证）

| 方向 | 原理 | 风险 |
|---|---|---|
| LLM Listwise 重排 | 一次喂入所有候选，LLM 比较排序 | 延迟高、成本高、离线部署困难 |
| 领域微调 Reranker | 用本项目标注数据 fine-tune | 标注成本，需要足够多的正负例 |
| 换 Reranker 模型 | jina-reranker-v3, mxbai-rerank 等 | 不确定性高，可能同样退化 |
| 接受基线 | 96.2% 已足够好 | 失去 Lexical 对精确 token 的贡献 |
| Hybrid (Dense + Lexical) 不用 Reranker | RRF 或加权融合 | 选型文档已验证 RRF 低于基线 |

## 6. 附录：关键数据文件

| 文件 | 说明 |
|---|---|
| `eval/pool50/lang-lexical/results.json` | 语言感知 Lexical 评测结果 |
| `eval/pool50/reranker-lang/results.json` | Reranker 评测结果 |
| `eval/pool50/reranker-concat/results.json` | 早期 Reranker 结果（query concat 版本） |
| `eval/pool50/lancedb-lang-index/` | 语言感知 LanceDB 索引 |
| `eval/pool50/run_lang_lexical.py` | 语言感知 Lexical 评测脚本 |
| `eval/pool50/run_reranker.py` | Reranker 评测脚本 |
| `docs/2026-07-28-issue-48-retrieval-backend-selection.md` | 后端选型文档 |
| `docs/2026-07-28-offline-en-zh-translator-selection.md` | 翻译服务选型文档 |
