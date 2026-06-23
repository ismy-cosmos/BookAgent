# BookAgent

**高效自动化知识蒸馏与智能体生成管线**

将任意学科书籍资料（PDF、图表、音频）自动转化为可在消费级硬件本地运行的专属智能体。

## 核心流程

```
原始书籍
  ├── PDF / 图文 ──→ 多模态解析层（Marker + Qwen3-vl-8b）
  └── 音频       ──→ 本地 ASR（Faster-Whisper）
         ↓
  自适应语义分块 & 学科元数据标注
         ↓
  轻量化知识蒸馏 / 结构化
         ↓
  智能体配置生成（system prompt + 工具链 + GGUF 量化）
         ↓
  Ollama 一键部署
```

## 目标指标

| 维度 | 目标 | 对比基线 |
|------|------|----------|
| Token 消耗 | ≤ 基线 60% | LangChain + 朴素 RAG + Qwen-8B-Instruct |
| 处理速度 | ≥15 页/分钟 | 同上 |
| 一键部署 | 成功率 100% | 传统 Docker+Ollama+Python 配置 |
| Hit@5 | ≥85%（3类学科）| 通用 Agent 方案 |
| 幻觉率 | ≤15% | 同上 |

## 硬件要求

- RAM ≥ 32GB
- VRAM ≥ 6GB（推荐；支持无 GPU 降级至 CPU 推理）
- NVMe SSD ≥ 500GB

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 处理书籍
python pipeline/run.py --input path/to/book.pdf

# 启动智能体
ollama run bookagent
```

## 项目结构

```
BookAgent/
├── pipeline/          # 主处理管线
│   ├── parse/         # 多模态解析层
│   ├── chunk/         # 语义分块
│   ├── embed/         # 向量化与检索
│   └── agent/         # 智能体配置生成
├── deploy/            # Ollama 部署脚本
├── eval/              # 评测脚本与数据集
└── docs/              # 技术文档
```

## 基础模型

- **VLM**：Qwen3-vl-8b（表格 / 公式 / 复杂图处理）
- **ASR**：Faster-Whisper / Whisper.cpp（本地音频转写）
- **量化**：Q4\_K\_M / Q5\_K\_S（消费级显存优化）
- **检索**：双阶段 Retrieve + Rerank（bge-reranker）
