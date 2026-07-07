# 内嵌图片VLM描述回填 真实数据端到端审读报告

**日期：** 2026-07-06
**分支：** `feat/vlm-figure-routing`（8 commit，315 单元测试全绿）
**范围：** 三阶段ingest架构（解析→VLM批量描述→分块入库）+ resize（2048px上限）真实数据验证

---

## 测试方式

真实调用`scripts/ingest.py`（非手动拼接parse→chunk），干净chroma目录（`/tmp/chroma-e2e`），本机真实GPU+真实Ollama（`qwen3:q4km`）：

```bash
rm -rf /tmp/chroma-e2e
bookagent.venv/bin/python3 scripts/ingest.py --book-id e2e-books --chroma-dir /tmp/chroma-e2e --dir eval/testset/cs/raw/book/
```

语料：`eval/testset/cs/raw/book/`全部9个文件（8个OSTEP CS章节PDF + 1个`java-ch1-e2e.epub`）。

**未测部分**：`eval/parser_selection/fixtures/raw/`下的法律/临床原书本次不测——临床那本（`Bookshelf_NBK595000.pdf`，146MB/965页，整本教材而非章节级）触发系统OOM killer杀死进程（已提[issue #24](https://github.com/ismy-cosmos/BookAgent/issues/24)记录，属marker自身单文件解析内存上限问题，与本次VLM工作无关），且这两本书没有对应QA测试集，本轮决定跳过，留待issue #24有方案后再补测。

## 端到端统计（真实运行结果）

| 阶段 | 耗时 | 说明 |
|---|---|---|
| 阶段1 解析 | 140.8s | 9个文件（109页PDF + 1个EPUB），marker layout/OCR |
| 阶段2 VLM批量描述 | 345.9s | 40张图，成功40/降级0/无字节跳过0（100%成功率） |
| 阶段3 分块+嵌入+入库 | 16.4s | 414 chunks |
| **总计** | **503.1s** | |

**页/分钟对照项目目标（≥15页/分钟）**：

- 纯解析（阶段1）：109页/140.8s = **46.4页/分钟**（超标3倍+）
- 含图文全流程（阶段1+2+3）：109页/503.1s = **13.0页/分钟**（未达标，差13%）

VLM阶段占全流程耗时68.8%，单图均耗8.65秒，是纯文本单页解析耗时（1.29秒/页）的6.7倍。这是"含VLM的端到端速度"与"纯文本解析速度"两个不同指标是否要分开考核的产品决策点，不是bug。

**Token消耗**：本次运行未采集（`describe_image`的`on_usage`回调是运行后才补的instrumentation，见后续commit）。已确认代码里`FigureBatchStats.per_image_tokens`能正确记录真实`usage.prompt_tokens`（见`tests/parse/test_figure_batch.py`新增用例），但要拿到这批语料的真实token数字需要重新跑一次ingest（sha去重，同一批文件不会重新触发VLM）。

## 人式审读结果（40个figure chunk全量审读，不套预设规则）

### 整体质量：好

对照OSTEP教材已知内容（进程状态图、内存层级、Gantt调度图、页表结构、PTE位布局、地址翻译流程等），VLM生成的描述**技术内容准确、结构清晰**，能正确识别图中的标签、数值、箭头指向关系，不是空泛套话。例如`vm-paging.pdf`的页表/PTE位布局描述、`cpu-sched.pdf`系列Gantt图的时间轴数值都对得上原书内容。

### 发现1：caption-aware prompt context按预期生效，但产生重复内容（40个中5个，12.5%）

跟`Figure N:/Table N:`说明行相邻的图片，把caption喂进VLM prompt这个机制本身生效了——但副作用是VLM经常在自己生成的描述**开头复述一遍caption**（改写过的版本，如"Figure 26.1: Single-Threaded And Multi-Threaded Address Spaces"），而chunker既有的caption-aware拼接逻辑又会在**结尾再原样拼一次**caption元素的原文——同一个caption信息在同一个chunk里出现两次（开头VLM转述版 + 结尾原文版）。

实测命中：`cpu-sched.pdf/p0004/0013`、`threads-intro.pdf/p0002/0001`、`vm-paging.pdf/p0004/0011`、`vm-paging.pdf/p0011/0037`、`vm-segmentation.pdf/p0002/0002`。

这是设计阶段没预料到的副作用——原意是"给VLM上下文帮助理解"，没想到模型会把上下文复述进自己的输出。不影响正确性（两次都是同一个caption，没有冲突信息），但浪费token、读起来略显冗余。**未修复，先记录**，是否要处理（比如prompt里明确要求"不要复述caption原文"）待决定。

### 发现2：alt文本补充信号机制生效，且暴露出`java-ch1-e2e.epub`里两张图疑似合成测试图

`java-ch1-e2e.epub/p0005/0038`（`alt: x`）和`/p0005/0039`（`alt: x+1`）——alt文本是"x"/"x+1"这种非自然语言占位符，不像真实书籍作者会写的alt文本，加上文件名本身带"e2e"字样，这两张图大概率是早期测试阶段插入的合成/示意图片，不是真实Java教材内容。

VLM对这两张抽象/模糊图片的描述**没有自信满满地瞎编**，而是恰当地加了大量hedge语言（"may represent"、"most likely represents"、"cannot be evaluated as a valid mathematical statement"），对`alt: x`那张甚至明确说"不包含任何可辨识的文字、公式、图表"——这是面对语义模糊内容时期望的行为，不是质量问题。

### 发现3：EPUB内嵌图片描述覆盖了代码截图、流程图、中英混排图（`java-ch1-e2e.epub`）

`p0004/0019`（Unix管道命令截图）、`p0004/0023`（Java方法+排序图）、`p0005/0036`（新旧FileFilter写法对比）、`p0006/0072`（中文"线程1/线程2"并发时序图）、`p0006/0074`（"分支/筛选"中文并行处理流程图）——VLM正确识别并转述了图中的代码内容、中文标注、多阶段流程结构，中英混排场景没有出现语言混乱或遗漏。

### 发现4：字节获取100%成功，尚未触发"静默降级"路径

40张图全部成功拿到`image_bytes`并成功描述，`no_bytes=0`、`degraded=0`——意味着spec里设计的"尽力而为+静默降级"这条容错路径，本次真实数据里完全没有被触发过，其正确性目前只有单元测试（mock）覆盖，没有真实数据验证。同样，`VLM_MAX_CONSECUTIVE_FAILURES`熔断机制本次也没有真实触发场景（Ollama全程无失败）。

## 问题清单汇总

| # | 问题 | 严重程度 | 处置 |
|---|---|---|---|
| 1 | 含VLM全流程13.0页/分钟，未达≥15页/分钟目标（纯解析46.4页/分钟达标） | 待决策 | 记录，待决定是否分开考核纯解析/含VLM两条速度指标 |
| 2 | caption-aware prompt context导致5/40 (12.5%) chunk出现caption重复内容 | 低（不影响正确性，浪费token+冗余） | 记录，未修复 |
| 3 | 本次token消耗未采集（instrumentation运行后才补） | 待补测 | 需重新跑ingest（换新book_id或清库）拿真实token数字 |
| 4 | 静默降级/熔断路径本次真实数据未触发，仅有mock测试覆盖 | 低 | 记录，非本次阻塞项 |
| 5 | 法律/临床原书未测（issue #24 OOM + 无QA测试集） | 中 | 待issue #24有方案后补测 |

## 结论

VLM描述内容质量达到可用标准，图片字节获取机制（marker `rendered.images` + EPUB `ebooklib`）在真实语料上100%成功。caption重复是唯一需要产品决策的质量问题；速度目标是否达标取决于"是否把VLM耗时计入核心指标"这一口径选择。建议在此基础上进行QA测试集端到端问答验证。
