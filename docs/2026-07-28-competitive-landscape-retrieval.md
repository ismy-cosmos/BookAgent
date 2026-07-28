# 同类产品检索能力对比与 BookAgent 定位

**日期**: 2026-07-28
**目的**: 回答"我们的测试集在同类产品中表现如何"——对比对象是"把文档材料变成可问答本地 AI"的产品，不是 IR 学术 benchmark。

## 1. 同类产品概览

调研了 2025-2026 年活跃维护的本地/离线文档问答产品，按成熟度排列：

| 产品 | Stars | 部署方式 | 离线 | 定位 |
|---|---|---|---|---|
| Open Notebook | 25K+ | Docker | ✅ (Ollama) | NotebookLM 开源替代 |
| nano-NotebookLM | 2K+ | Docker / HF Space | ✅ (Ollama) | 学习场景深度阅读 |
| NotebookLM-Lite | — | FastAPI + SeekDB | ✅ | NotebookLM 风格工作台 |
| PrivateGPT | 50K+ | Python | ✅ | 最早一批本地文档 AI |
| AnythingLLM | 30K+ | Docker / Desktop | ✅ | 多模型 + 多格式 RAG |
| LocalGPT | — | Python CLI | ✅ | 极简本地 RAG |

## 2. 检索架构对比

| 维度 | nano-NotebookLM | Open Notebook | BookAgent |
|---|---|---|---|
| **Dense 检索** | FAISS + bge-m3 | SurrealDB + 可配 embedding | ChromaDB + bge-m3 |
| **Lexical 检索** | BM25 | "全文搜索"（未详述） | **LanceDB FTS + Jieba 分词 + 语言感知路由 + Argos 翻译** |
| **融合策略** | **RRF**（等权） | 未公开 | **已验证 RRF 低于基线，不采用** |
| **Reranker** | 无 | 无 | **bge-reranker-v2-m3（评测后决定不启用）** |
| **检索质量评测** | **无公开指标** | **无公开指标** | **strict-ID Hit@5 = 96.2%**（211 题 auditor 标注） |
| **多语言** | bge-m3 多语言 | 依赖 provider | **中英混合 + 语言感知路由 + 术语保护翻译** |
| **引用粒度** | 页码（"Page 32/51"） | "基础引用（将改进）" | **页码 + 音频秒级时间戳 + 六类 element_type** |

## 3. 检索质量：同类产品没有可对比的指标

调研的核心发现：**同类产品均不发布检索质量 benchmark**。

- Open Notebook 的 citations 自评 "Basic references (will improve)"
- nano-NotebookLM 的 RRF 融合方案——正是我们 P3 消融实验中证明**低于基线**的方案（179/186 vs 184/186）
- 没有任何竞品公布过类似我们的 strict-ID Hit@5 或 auditor 标注的 ground truth 数据集

这意味着：
- **我们无法知道竞品的检索质量好不好**——它们没有评测
- **竞品也不知道自己的检索质量**——没有 ground truth，无法量化
- **BookAgent 的 96.2% 在同类产品中是唯一有数据支撑的数字**——不是因为它一定最高，是因为只有我们做了系统评测

## 4. 我们的测试集是否太特殊

### 4.1 查询特征

| 特征 | 我们的测试集 | 同类产品的典型使用场景 |
|---|---|---|
| Query 长度 | 平均 123 字符 | 短句/关键词为主 |
| Query 来源 | 真实教材阅读 trace | 用户自由输入 |
| 语言 | 中英混合（49%含中文） | 以英语为主 |
| 领域 | CS/临床/法学教材 | 不限（用户自传文档） |
| 评估指标 | strict-ID chunk 匹配 | 主观感受 |

### 4.2 难度分析

**我们的测试集对检索系统来说偏"简单"**——检索空间受限（单书内），教材结构规整，query 信息丰富。这也是 baseline 能达到 96.2% 的原因之一。

**但对 Reranker 来说偏"难"**——baseline 已经接近理论最大值（99.1%），只剩 6 个可改进空间。Reranker 需要在 30-50 个高度相似的教材相邻段落中精确挑出 auditor 标注的那一个——strict-ID 不奖励"找了同章另一段"。

### 4.3 与竞品用户场景的差异

竞品的使用场景（学生上传讲义、研究者上传论文）可能 baseline 更低（文档质量参差、无结构），Reranker 反而可能有提升空间。但我们无法验证——竞品没有公开指标。

## 5. BookAgent 的检索优势

相对于同类产品，BookAgent 在检索层面有三个结构性优势：

### 5.1 有 ground truth 驱动的量化评测

这是最根本的差异。同类产品靠"感觉好用"来判断检索质量，BookAgent 有 211 题 auditor 标注的 strict-ID ground truth。这意味着：
- 每次架构变更都有数字反馈（不是"感觉快了"）
- 可以检测退化（Reranker -5.2%）
- 可以在三学科上统一评测（领域漂移可见）

### 5.2 语言感知 Lexical 检索

竞品要么只做 BM25（nano-NotebookLM），要么"全文搜索"语焉不详（Open Notebook）。BookAgent 的语言感知方案：
- Jieba 预分词修复中文 BM25
- en/zh 分字段索引避免 tokenizer 互相污染
- Argos Translate + 术语保护实现跨语言查询
- 已经过消融实验验证（Lexical Hit@5 从 62.4% → 78.9%）

### 5.3 RRF 已被验证不可行

nano-NotebookLM 正在用 RRF（"BM25 + FAISS + RRF"）——正是我们 P3 消融证明低于基线的方法。如果我们没有做消融，现在可能也在用 RRF 并以为"反正大家都这么用"。

## 6. 天花板与定位

```
同类产品：                     BookAgent：
"上传文档，问问题，感觉不错"     "上传教材，211 题 auditor 标注，96.2% 严格命中"
          ↓                              ↓
  没有量化标准                    唯一有 benchmark 的
  不知道哪儿不好                  知道退化在哪儿（-5.2%）
  改进靠直觉                      改进靠数据
```

BookAgent 的差异化不在"比别人检索更好"——我们不知道别人的检索好不好，因为它们没测。差异化在于**我们知道自己的检索好不好**，并且能通过评测驱动改进。

## 7. 关于在竞品测试集上验证

不存在"竞品测试集"——同类产品不发布 benchmark。从 IR 学术 benchmark 来看：
- bge-m3 是 MTEB 顶级模型，通用检索能力强
- 教材检索（结构化、空间受限）比开放 Web 检索更容易
- BookAgent 在教材上的 96.2% 可以作为一个参考锚点

但严格来说，**没有可对比的外部数据集**。如果要对外宣称检索质量，建自己的 benchmark 是唯一的路径——这正是我们已经在做的事。
