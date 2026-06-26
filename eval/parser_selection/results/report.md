# 解析器选型对比报告

## 1. 速度对比（原始）

| 解析器 | pages/min | p50 延迟(s) | p95 延迟(s) |
|---|---|---|---|
| unstructured | 236.0 | 0.18 | 1.032 |
| marker | 10.5 | 0.809 | 37.641 |

## 2. VLM 路由分析

图片页或双解析器均失败的页面将路由至 VLM，不计入解析器速度考核。

- **VLM 页数**：5 / 15
- **VLM 页面**：cl-03, cl-05, cs-04, cs-05, cs-06

| 解析器 | 有效页/min（剔除VLM页） | 达标(≥15) |
|---|---|---|
| unstructured | 210.9 | ✅ |
| marker | 16.2 | ✅ |

## 3. 人工评分汇总（满分 90）

| 解析器 | detect(/30) | content(/30) | struct(/30) | 总分(/90) |
|---|---|---|---|---|
| unstructured | 20 | 20 | 10 | 50 |
| marker | 25 | 27 | 23 | 75 |

## 4. 选定建议

✅ **选定：`marker`**（速度均达标；人工总分 75 > 50）

**下一步：** 在 `requirements.txt` 中取消 `marker` 注释，删除 `requirements-bench.txt`，合并 `feat/w1-parser-selection` → `main`。