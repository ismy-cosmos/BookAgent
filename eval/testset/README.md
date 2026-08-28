# 测试集说明

每个学科目录结构：

```
<subject>/
  raw/          # 原始文件（gitignored）
    audio/      # 音频片段 ≤5min，mp3/wav
    *.pdf       # 主教材章节
  qa/           # QA 标注集（tracked）
    qa.jsonl    # 每行一条 QA，字段见下
  chunks/       # ingest 生成的 chunk 清单（gitignored）
    chunks.jsonl
```

## QA 字段

| 字段 | 说明 |
|---|---|
| id | 样本唯一编号，如 cs-001 |
| subject | cs / clinical / law |
| question_type | 事实题 / 计算题 / 无答案题 / 音频题 |
| question | 问题文本 |
| standard_answer | 标准答案（无答案题为空） |
| supporting_chunks | 应命中的 chunk id 列表（用于 Hit@5） |
| source_location | 页码 / 章节 / 音频时间段 |

## 规模目标（Appendix A）

| 学科 | 主教材 | 音频 | QA 总数 | 事实/计算/无答案/音频 |
|---|---|---|---|---|
| CS | OSTEP ≥100p | 2–3 段 | 60–80 | ~40/10/10/5 |
| 临床医学 | ≥100p | 2–3 段 | 60–80 | ~40/10/10/5 |
| 法学 | ≥100p | 2–3 段 | 60–80 | ~40/10/10/5 |

## CS 测试集题量分布原则（2026-07-20 审查+扩容后）

无答案题占比按约15%设计，不是随意定的比例：这类题目专门用来测"检索不到相关内容时模型会不会诚实说明、还是自信编造"，是issue #40（retrieve无相关性阈值导致幻觉）最直接的诊断样本。分母定在15%左右，是希望全量幻觉率（幻觉数/全部题目数，不是幻觉数/无答案题数）能落在15%以内，跟真实审查测出的7.9%（6/76，仅统计模型完全没有披露"未查到依据"的情况）互相印证——具体方法论、逐题判定见`docs/test-report-2026-07-20-cs-testset-audit.md`开头的"全量结果汇总"一节。

音频题、图片题的数量不强行凑到某个固定比例——音频只有一段约5分钟的demo录音，图片只有3张可用素材，出多少道不重复的高质量题目由内容本身能撑住多少来定，不为了凑数而降低题目质量（比如把同一段内容拆成好几道细碎重复的题）。

**最终实际题量分布**（Task 3-13真实执行结果，76题）：

| 类型 | 数量 | 占比 |
|---|---|---|
| 事实题 | 49 | 64.5% |
| 计算题 | 11 | 14.5% |
| 无答案题 | 13 | 17.1% |
| 音频题 | 3 | 3.9% |
| **合计** | **76** | 100% |

来源分布：cpu-intro.pdf(7)、cpu-api.pdf(7)、cpu-sched.pdf(9)、cpu-sched-multi.pdf(6)、threads-intro.pdf(7)、threads-api.pdf(6)、vm-paging.pdf(9，含新增1题)、vm-segmentation.pdf(7)、音频segment-01(5)、java-ch1-e2e.epub(10，全部新增)、图片cs_p1~p3.png(3，全部新增)。

## 临床医学测试集题量分布原则（2026-07-22 构建完成后）

延续CS那套方法论：每道题都跑真实端到端管线核验，无答案题占比对齐issue #40幻觉诊断目标，音频/图片题数量由内容本身能撑住多少道高质量题决定，不强行凑固定比例或类型配比——比如ch18（抗高血压）全章没有mg/kg剂量数据就不出计算题，cli_p1.png（政府宣传页）没有实质临床知识点就不出题。逐题的检索query、score、能否支撑答案、回答准确性、幻觉判定见`docs/test-report-2026-07-22-clinical-testset-audit.md`，构建过程中发现的真实管线缺陷（幻觉案例、检索miss、MAX_ROUNDS_EXCEEDED、题面措辞导致模型跳过检索等）汇总在该文档的"缺陷清单"一节。

**最终实际题量分布**（89题）：

| 类型 | 数量 | 占比 |
|---|---|---|
| 事实题 | 60 | 67.4% |
| 音频题 | 11 | 12.4% |
| 无答案题 | 13 | 14.6% |
| 计算题 | 5 | 5.6% |
| **合计** | **89** | 100% |

来源分布：openstax-pharm-ch07-antiinfective.pdf(22)、openstax-pharm-ch13-psychopharm.pdf(20)、openstax-pharm-ch18-antihypertensive.pdf(15)、openstax-pharm-ch28-diabetic.pdf(16)、音频6段cardiac pharmacology网课(13)、图片cli_p2/p3.png(3，cli_p1.png未出题)。
