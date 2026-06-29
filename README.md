# BookAgent

**高效自动化知识蒸馏与智能体生成管线**

将任意学科书籍资料（PDF、图表、公式、音频）自动转化为可在消费级硬件本地运行、离线可用、引用可溯的专属智能体。

## 核心流程

```
原始书籍
  ├── PDF / EPUB ── 解析层（Unstructured / Marker + Qwen3-vl-8b 处理表格/公式/图）
  ├── 图片         ── VLM caption → Markdown/LaTeX
  └── 音频         ── WhisperX 本地 ASR（带时间戳，离线）
            ↓
  自适应语义分块 + 学科元数据标注
            ↓
  bge-m3 向量化 → ChromaDB（chunk + 元数据 + 向量三合一）
            ↓
  智能体层：retrieve / calculate 工具调用 + 引用溯源约束
            ↓
  Ollama Modelfile + GGUF 量化（Q4_K_M / Q5_K_S）→ 一键部署
```

## 目标指标

| 维度 | 目标 | 对比基线 |
|------|------|----------|
| Token 消耗 | ≤ 基线 60% | LangChain + 朴素 RAG + Qwen-8B-Instruct |
| 处理速度 | ≥15 页/分钟；≤2 分钟/音频（5min 以内） | 同上 |
| 一键部署 | 成功率 100% | 传统 Docker+Ollama+Python 手工配置 |
| Hit@5 | ≥85%（CS / 临床医学 / 法学） | 通用 Agent 方案 |
| 幻觉率 | ≤15% | 同上 |

## 硬件要求

- RAM ≥ 32GB
- VRAM ≥ 8GB 推荐（≥6GB 可用，部分层 offload CPU；支持纯 CPU 降级）
- NVMe SSD ≥ 500GB

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/ismy-cosmos/BookAgent
cd BookAgent

# 一键部署（自动检测环境、下载模型、构建知识库、自检）
./run.sh
```

## 项目结构

```
BookAgent/
├── pipeline/
│   ├── parse/         # 多模态解析层（PDF/图片/音频）
│   ├── chunk/         # 自适应语义分块
│   ├── embed/         # bge-m3 向量化 + ChromaDB
│   └── agent/         # 工具调用层（retrieve / calculate）
├── deploy/            # Modelfile + run.sh + deploy.ps1
├── eval/              # 评测脚本、测试题库、结果 CSV
└── docs/              # 技术文档与设计规格
```

## 技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| VLM | Qwen3-vl-8b | 表格 / 公式 / 复杂图处理 |
| ASR | WhisperX ≥3.8.4 | 本地转录 + 强制对齐 + 时间戳 |
| 向量化 | BAAI/bge-m3 | dense 1024 维，多语种，CPU 可用 |
| 精排 | bge-reranker-v2-m3 | 两阶段检索的 cross-encoder 精排 |
| 向量库 | ChromaDB（嵌入式） | chunk + 元数据 + 向量三合一 |
| 推理服务 | Ollama | OpenAI 兼容工具调用 API |
| 量化 | Q4_K_M（默认）/ Q5_K_S | 消费级显存优化 |

