# 解析器选型实测对比 — 设计文档

**日期**：2026-06-26  
**分支**：`feat/w1-parser-selection`  
**里程碑**：W1 任务（§C.8 解析器遴选，原计划 W1 延至此完成）  
**决策目标**：在 Unstructured 与 Marker-pdf 之间选定 W2 主干默认解析器，并在同一分支产出 `pipeline/parse/` 抽象接口骨架。

---

## 1. 背景与约束

项目规格书 §C.8 要求：在正式进入 W2 主干（parse → chunk → embed 管线）之前，通过小样本实测确定默认解析器，接口抽象为 `parse(pdf) -> elements`，支持随时切换。

候选解析器：

| 解析器 | 许可 | Python 约束 | 元素输出 |
|---|---|---|---|
| Unstructured | Apache-2.0 | 无上界 | 带 `type` 标签的结构化元素 |
| Marker-pdf | GPL / cc-by-nc-sa | ≤ 3.12 | Markdown 输出，含 LaTeX 公式 |

本项目使用 Python 3.12，两者均可安装。许可差异作为决策因素之一（不直接淘汰，以实测表现为主）。

---

## 2. 目录结构

```
eval/parser_selection/
├── fixtures/
│   ├── raw/                  # 原始书籍 PDF（已下载）
│   │   ├── cs/               # OSTEP 章节
│   │   ├── clinical/         # Nursing Pharmacology 2e
│   │   └── law/              # Criminal Procedure (CALI)
│   ├── pages/                # extract_pages.py 产出（15 个单页 PDF）
│   └── gt/                   # Ground Truth JSON（15 个，手工标注）
├── scripts/
│   ├── pages.json            # 15 页配置（文件名 + 页号 + 元素类型）
│   ├── extract_pages.py      # 从源 PDF 裁出 15 单页
│   ├── run_bench.py          # 跑两个解析器 + 计时 + 保存输出
│   └── gen_report.py         # 自动指标 + scorecard → report.md
├── results/
│   ├── unstructured/         # 解析输出（每页一个 JSON）
│   ├── marker/               # 解析输出（每页一个 JSON）
│   └── scorecard.csv         # 人工打分表（run_bench.py 生成骨架）
└── textbook-candidates.md    # 语料候选记录

pipeline/parse/               # 同分支新建（接口原型）
├── __init__.py
├── base.py                   # Element dataclass + Parser ABC
├── unstructured.py           # Unstructured 适配器（benchmark 后填充）
└── marker.py                 # Marker 适配器（benchmark 后填充）
```

---

## 3. 样本页（15 页）

### 3.1 页面配置（pages.json 内容）

| ID | 来源文件 | 页号 | 元素类型 | 解析难点 |
|---|---|---|---|---|
| cs-01 | `cs/cpu-sched.pdf` | 2 | 纯正文 | 密集假设列表段落 |
| cs-02 | `cs/threads-intro.pdf` | 4 | 代码块 | C/pthread `#include` 多段代码 |
| cs-03 | `cs/threads-intro.pdf` | 10 | 执行追踪表 | Thread 1/2/PC/eax/counter 多列表格 |
| cs-04 | `cs/vm-paging.pdf` | 4 | 计算/公式 | VPN/offset 位宽数学推导 |
| cs-05 | `cs/vm-paging.pdf` | 7 | 位域结构图 | x86 PTE 位位置标注（31\|12\|…\|0） |
| cs-06 | `cs/cpu-intro.pdf` | 6 | 状态机图 | Running/Ready/Blocked + Figure caption |
| cl-01 | `clinical/Bookshelf_NBK595000.pdf` | 33 | 纯正文 | 药代动力学四阶段概述 |
| cl-02 | `clinical/Bookshelf_NBK595000.pdf` | 318 | 多列药物表格 | Table 4.7 五列 Medication Grid，单元格多行 |
| cl-03 | `clinical/Bookshelf_NBK595000.pdf` | 53 | PK 曲线图 | Figure 1.6 半衰期药时曲线 + caption |
| cl-04 | `clinical/Bookshelf_NBK595000.pdf` | 70 | 剂量/稳态文字 | 半衰期定量描述，含隐式公式 |
| cl-05 | `clinical/Bookshelf_NBK595000.pdf` | 271 | 结构化药物条目 | Vancomycin Route/Dose/Check 嵌套结构 |
| lw-01 | `law/Criminal-Procedure-July2022_0.pdf` | 23 | 案件引用索引 | `Case v. Case, ### U.S. ### (####) ···##` 密集列表 |
| lw-02 | `law/Criminal-Procedure-July2022_0.pdf` | 25 | 纯正文 | Chapter 1 Introduction 叙述段 |
| lw-03 | `law/Criminal-Procedure-July2022_0.pdf` | 27 | 案例分析文本 | Ed Brown v. Mississippi 引用 + 法律推理 |
| lw-04 | `law/Criminal-Procedure-July2022_0.pdf` | 42 | 修正案/法条 | Chapter 2 第四修正案原文 + Katz 分析 |

### 3.2 元素类型分布

| 类型 | 数量 | 覆盖学科 |
|---|---|---|
| 纯正文 | 3 | CS / 临床 / 法学各 1 |
| 代码块 | 1 | CS |
| 执行追踪表 / 多列表格 | 2 | CS / 临床 |
| 计算公式 / 位域结构 | 2 | CS |
| 图 + caption | 2 | CS / 临床 |
| 结构化条目 | 2 | 临床 / 法学 |
| 案件引用索引 | 1 | 法学 |
| 案例分析 | 1 | 法学 |
| 修正案法条 | 1 | 法学 |

---

## 4. 脚本设计

### 4.1 `extract_pages.py`

- 读 `scripts/pages.json`，用 `pypdf.PdfWriter` 裁出每页为独立 PDF
- 输出至 `fixtures/pages/<id>.pdf`（如 `cs-01.pdf`）
- 幂等：已存在则跳过

### 4.2 `run_bench.py`

对 15 个单页 PDF，依次：

1. 用 Unstructured 解析 → 记录耗时 + 输出 Element 列表
2. 用 Marker 解析 → 记录耗时 + 输出 Markdown/JSON
3. 统一序列化为 `results/<parser>/<id>.json`，结构：

```json
{
  "id": "cs-01",
  "parser": "unstructured",
  "elapsed_sec": 0.42,
  "char_count": 1823,        // 参考字段：粗略完整度代理，不参与评分；Markdown 格式符会虚胀 Marker 的值
  "elements": [
    {"type": "text", "content": "...", "page_num": 1}
  ]
}
```

4. 生成 `results/scorecard.csv` 骨架（15 行，`detect`/`content`/`struct` 列留空）

两个解析器在独立 try/except 内运行，任一失败记录错误不中断。

### 4.3 `gen_report.py`

- 读 `results/unstructured/*.json` + `results/marker/*.json` + `scorecard.csv`
- 输出 `results/report.md`，含：
  - 速度对比表（pages/min，p50/p95 延迟）
  - 字符数完整度对比
  - 人工评分汇总（detect/content/struct 三维 × 两解析器）
  - 最终建议行（满足速度目标且人工总分更高者胜出）

---

## 5. 人工打分规则

打分表 `scorecard.csv` 每行对应一个（页 × 解析器）组合，共 30 行（15 页 × 2）。

| 列 | 含义 | 0 | 1 | 2 |
|---|---|---|---|---|
| `detect` | 元素类型识别 | 完全错 | 部分对 | 完全对 |
| `content` | 内容完整准确 | 严重缺失/乱码 | 部分缺失 | 完整 |
| `struct` | 结构保留（表/代码/公式）| 结构丢失 | 结构部分 | 结构完整 |

每页满分 6 分，两解析器各自满分 90 分。结构列（`struct`）对无结构元素（纯正文/案例分析）默认给 2 分。

预计打分时间：30–40 分钟。

---

## 6. `pipeline/parse/` 接口规格

### 6.1 `Element` dataclass

```python
@dataclass
class Element:
    type: str        # "text" | "table" | "formula" | "figure" | "code"
    content: str     # Markdown / LaTeX / plain text
    page_num: int    # 1-indexed
    metadata: dict   # {"caption": str, "confidence": float, ...}
```

### 6.2 `Parser` ABC

```python
class Parser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[Element]: ...
```

### 6.3 设计约束

- 接口不涉及 VLM（表格/公式转 LaTeX 是 chunk 层下游步骤）
- 适配器（`unstructured.py` / `marker.py`）在 benchmark 结束、胜出者确定后填充
- `parse()` 的调用方仅依赖 `Element` 结构，不感知底层解析器

---

## 7. 决策规则

在 `gen_report.py` 输出报告后，按优先级逐项判断：

1. **速度**：≥ 15 页/分钟（任一不达标则直接出局；两者均达标则继续）
2. **人工总分**：90 分满分，总分高者优先
3. **许可**：同分时 Apache-2.0（Unstructured）优于 GPL（Marker）
4. **安装复杂度**：依赖链更短者优先

结论写入 `results/report.md` 最后一节，同时更新 `requirements.txt` 中注释掉的解析器行为正式依赖。

---

## 8. 与 W5 消融实验的复用关系

| 本次产出 | W5 复用方式 |
|---|---|
| `scripts/pages.json` 的 GT 格式 | W5 全量题库沿用同一 JSON 结构 |
| `run_bench.py` 计时/采集框架 | `run_ablation.py` 照搬循环结构 |
| `gen_report.py` 报告模板 | W5 消融报告同格式，评委直接对比 |

---

## 9. 里程碑与验收

| 步骤 | 产出 | 完成标志 |
|---|---|---|
| extract_pages | 15 个单页 PDF | `fixtures/pages/` 含 15 个文件 |
| run_bench | 30 个结果 JSON + scorecard 骨架 | `results/` 无报错 JSON，CSV 有 30 行骨架 |
| 人工打分 | scorecard.csv 填完 | 无空白单元格 |
| gen_report | report.md | 含速度表 + 评分汇总 + 建议行 |
| 接口原型 | `pipeline/parse/` 四文件 | `from pipeline.parse import Parser, Element` 可导入 |
| PR | feat/w1-parser-selection → main | 胜出解析器写入 requirements.txt |
