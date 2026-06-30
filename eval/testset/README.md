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
