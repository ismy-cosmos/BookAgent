# 内嵌图片VLM描述回填 真实数据端到端审读报告

**日期：** 2026-07-06
**分支：** `feat/vlm-figure-routing`（14 commit，315 单元测试全绿，[PR #26](https://github.com/ismy-cosmos/BookAgent/pull/26)）
**范围：** 三阶段ingest架构（解析→VLM批量描述→分块入库）+ resize（2048px上限）真实数据验证

---

## 测试方式

真实调用`scripts/ingest.py`（非手动拼接parse→chunk），干净chroma目录，本机真实GPU+真实Ollama（`qwen3:q4km`）。跑了两次：首次（`/tmp/chroma-e2e`）用于统计耗时和人式审读；token instrumentation（commit `85f5750`）补上后，二次（`/tmp/chroma-e2e-tok`）用同样语料重新跑了一遍，专门补采token数据：

```bash
rm -rf /tmp/chroma-e2e-tok
bookagent.venv/bin/python3 scripts/ingest.py --book-id e2e-books --chroma-dir /tmp/chroma-e2e-tok --dir eval/testset/cs/raw/book/
```

语料：`eval/testset/cs/raw/book/`全部9个文件（8个OSTEP CS章节PDF + 1个`java-ch1-e2e.epub`）。

**未测部分**：`eval/parser_selection/fixtures/raw/`下的法律/临床原书本次不测——临床那本（`Bookshelf_NBK595000.pdf`，146MB/965页，整本教材而非章节级）触发系统OOM killer杀死进程（已提[issue #24](https://github.com/ismy-cosmos/BookAgent/issues/24)记录，属marker自身单文件解析内存上限问题，与本次VLM工作无关），且这两本书没有对应QA测试集，本轮决定跳过，留待issue #24有方案后再补测。

## 端到端统计（真实运行结果）

首次运行（`/tmp/chroma-e2e`）未采集token（instrumentation当时还没写）；补上instrumentation后（commit `85f5750`）用干净目录（`/tmp/chroma-e2e-tok`）重新跑了一次同样语料，两次运行耗时高度一致，token数据来自第二次：

| 阶段 | 首次运行耗时 | 二次运行耗时 | 说明 |
|---|---|---|---|
| 阶段1 解析 | 140.8s | 141.8s | 9个文件（109页PDF + 1个EPUB），marker layout/OCR |
| 阶段2 VLM批量描述 | 345.9s | 343.7s | 40张图，成功40/降级0/无字节跳过0（100%成功率，两次一致） |
| 阶段3 分块+嵌入+入库 | 16.4s | 15.9s | 414 chunks（两次一致） |
| **总计** | **503.1s** | **501.4s** | |

**页/分钟对照项目目标（≥15页/分钟）**（以二次运行为准）：

- 纯解析（阶段1）：109页/141.8s = **46.1页/分钟**（超标3倍+）
- 含图文全流程（阶段1+2+3）：109页/501.4s = **13.0页/分钟**（未达标，差13%，与首次运行结论一致）

VLM阶段占全流程耗时68.5%，单图均耗8.6秒，是纯文本单页解析耗时（1.30秒/页）的6.6倍。这是"含VLM的端到端速度"与"纯文本解析速度"两个不同指标是否要分开考核的产品决策点，不是bug。

**Token消耗（真实数据，`usage.prompt_tokens`）**：40张图**总计45286 token，平均1132 token/图**，单张范围符合此前resize校准阶段的实测区间（2048px图片约2772 token，实际书内嵌图多数小于2048px，故均值低于该上限）。40张图全部成功，没有失败样本可比对token与失败率的关系。

## 人式审读结果（40个figure chunk全量审读，不套预设规则）

### 整体质量：好

对照OSTEP教材已知内容（进程状态图、内存层级、Gantt调度图、页表结构、PTE位布局、地址翻译流程等），VLM生成的描述**技术内容准确、结构清晰**，能正确识别图中的标签、数值、箭头指向关系，不是空泛套话。例如`vm-paging.pdf`的页表/PTE位布局描述、`cpu-sched.pdf`系列Gantt图的时间轴数值都对得上原书内容。

### 发现1：caption-aware prompt context按预期生效，但产生重复内容（40个中5个，12.5%）

跟`Figure N:/Table N:`说明行相邻的图片，把caption喂进VLM prompt这个机制本身生效了——但副作用是VLM经常在自己生成的描述**开头复述一遍caption**（改写过的版本，如"Figure 26.1: Single-Threaded And Multi-Threaded Address Spaces"），而chunker既有的caption-aware拼接逻辑又会在**结尾再原样拼一次**caption元素的原文——同一个caption信息在同一个chunk里出现两次（开头VLM转述版 + 结尾原文版）。

实测命中：`cpu-sched.pdf/p0004/0013`、`threads-intro.pdf/p0002/0001`、`vm-paging.pdf/p0004/0011`、`vm-paging.pdf/p0011/0037`、`vm-segmentation.pdf/p0002/0002`。

这是设计阶段没预料到的副作用——原意是"给VLM上下文帮助理解"，没想到模型会把上下文复述进自己的输出。不影响正确性（两次都是同一个caption，没有冲突信息），但浪费token、读起来略显冗余。**未修复，先记录**，是否要处理（比如prompt里明确要求"不要复述caption原文"）待决定。

### 发现2：极小的行内排版图片被VLM过度解读，产生真实幻觉案例

`java-ch1-e2e.epub/p0005/0038`（`alt: x`）和`/p0005/0039`（`alt: x+1`）——已直接查证EPUB源HTML确认真实来历：原文讲解Java 8 lambda语法，句子"你现在可以写`(int x) -> x + 1`，表示'调用时给定参数[图]，就返回[图]值的函数'"里，变量名`x`和表达式`x+1`被原书排版成了两张行内小GIF图片（`00006.gif`/`00007.gif`），alt文本就是图片实际内容——这是原书真实排版产物，**不是测试图或异常数据**。

真正的问题是：VLM面对这种本质上只是"一个字母/一个简单表达式"的排版级小图，**没能识别出其简单身份，反而给出了自信但完全偏离事实的复杂解读**——alt为`x`的图被描述成"黑白抽象构图、模糊几何形状、类T字形轮廓……"；alt为`x+1`的图被解读成"积分符号+加号+绝对值符号"，还煞有介事地推导出"这是一个数学上不完整的积分表达式"。这是一次**真实的幻觉案例**：有简单确定的真实内容，模型却给出了自信的错误解读，不是"语义模糊时的合理hedge"。

可能根因：这类图片原始尺寸极小（行内单字符/短表达式排版用图），现有resize只处理"过大"（长边>2048px），没有处理"过小"的情况，小图被视觉编码器处理时可能因插值/放大失真导致误读。是否需要对过小的图做特殊处理（比如低于某阈值时不送VLM、直接保留原始文字/alt文本）待决定，**未修复，先记录**。已提[issue #25](https://github.com/ismy-cosmos/BookAgent/issues/25)跟踪。

### 发现3：EPUB内嵌图片描述覆盖了代码截图、流程图、中英混排图（`java-ch1-e2e.epub`）

`p0004/0019`（Unix管道命令截图）、`p0004/0023`（Java方法+排序图）、`p0005/0036`（新旧FileFilter写法对比）、`p0006/0072`（中文"线程1/线程2"并发时序图）、`p0006/0074`（"分支/筛选"中文并行处理流程图）——VLM正确识别并转述了图中的代码内容、中文标注、多阶段流程结构，中英混排场景没有出现语言混乱或遗漏。

### 发现4：字节获取100%成功，尚未触发"静默降级"路径

40张图全部成功拿到`image_bytes`并成功描述，`no_bytes=0`、`degraded=0`——意味着spec里设计的"尽力而为+静默降级"这条容错路径，本次真实数据里完全没有被触发过，其正确性目前只有单元测试（mock）覆盖，没有真实数据验证。同样，`VLM_MAX_CONSECUTIVE_FAILURES`熔断机制本次也没有真实触发场景（Ollama全程无失败）。

## 问题清单汇总

| # | 问题 | 严重程度 | 处置 |
|---|---|---|---|
| 1 | 含VLM全流程13.0页/分钟，未达≥15页/分钟目标（纯解析46.1页/分钟达标） | 待决策 | 记录，待决定是否分开考核纯解析/含VLM两条速度指标 |
| 2 | caption-aware prompt context导致5/40 (12.5%) chunk出现caption重复内容 | 低（不影响正确性，浪费token+冗余） | 记录，未修复 |
| 3 | 极小的行内排版图片（单字符/短表达式）被VLM过度解读，产生真实幻觉（自信但错误的描述） | 中（chunk内容与真实图片完全不符，会污染检索） | 记录，未修复；已提[issue #25](https://github.com/ismy-cosmos/BookAgent/issues/25)，可能需要按图片尺寸做特殊处理 |
| 4 | ~~本次token消耗未采集~~ | 已解决 | 已补测：40张图总计45286 token，平均1132/图，见上"端到端统计" |
| 5 | 静默降级/熔断路径本次真实数据未触发，仅有mock测试覆盖 | 低 | 记录，非本次阻塞项 |
| 6 | 法律/临床原书未测（issue #24 OOM + 无QA测试集） | 中 | 待issue #24有方案后补测 |

## 结论

图片字节获取机制（marker `rendered.images` + EPUB `ebooklib`）在真实语料上100%成功，真实token消耗已补测（40张图45286 token，均1132/图）。VLM描述对正常尺寸的技术图表（Gantt图、内存布局、页表结构等）质量好、技术细节准确；但对极小的行内排版图片（发现2，issue #25）会产生自信但错误的幻觉描述，这类内容一旦进入检索库有污染答案的风险，不是可以忽略的边角案例。caption重复（发现1）是需要产品决策的次要质量问题；速度目标是否达标取决于"是否把VLM耗时计入核心指标"这一口径选择。

**QA测试集端到端问答验证已执行**（用户用`ask_cli.py`跑了8轮真实多轮对话，含专门验证VLM图片理解的题目）：发现的问题全部指向agent多轮工具调用可靠性（该retrieve却不retrieve+伪造引用，包括编造不存在的文件名），是已有[issue #17](https://github.com/ismy-cosmos/BookAgent/issues/17)（已用本次数据追加复现证据），与本次VLM图片路由实现质量无关。但这也意味着"VLM图片理解对最终问答质量的实际贡献"目前还没有被端到端验证过——每次尝试验证都被#17这个bug拦住（该调用retrieve时模型跳过了，图片内容根本没被读到），需要#17解决后才能补验证。
