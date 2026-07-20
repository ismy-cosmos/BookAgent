# CS测试集审查+扩容：真实管线审查记录

记录审查`eval/testset/cs/qa/qa.jsonl`过程中，用真实端到端管线（`book_id=cs-eval`，`answer()`，`qwen3:q4km`）对每道题的检索质量核验结果。审查方法：`eval/audit_question.py`跑真实`answer()`，逐个citation核对`score`（ChromaDB cosine距离，越小越相关）和chunk全文是否真能推出标准答案。

格式：每题按"题号+题目原文+score表格+回答是否准确+具体分析"记录；跨题目的共性问题（不针对某一道题）统一放最后"遇到的问题"一节，不为这些问题单独开GitHub issue——issue #40（retrieve无相关性阈值）本身就是冲着这类问题去的，现在暴露出的检索/幻觉现象是预期中会被后续修复的对象。

## cpu-intro.pdf 章节（Task 3，2026-07-20）

### cs-b001

**题目**："What is the operating system's precise definition of a 'process'? What is the difference between a process and a program?"

**检索query**："operating system definition of process and difference between process and program"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0001/0000` | 0.2615 | 能（进程定义核心段） |
| `cpu-intro.pdf/p0002/0002` | 0.2950 | 能（machine state细化，支撑"跟程序的区别"） |
| `cpu-intro.pdf/p0004/0005` | 0.3587 | 部分能（进程创建加载步骤，非定义本身） |
| `cpu-intro.pdf/p0009/0016` | 0.3789 | 部分能（ASIDE总结，含定义相关内容） |
| `cpu-intro.pdf/p0007/0013` | 0.3900 | 不能（讲PCB数据结构，非定义/区别） |

**回答是否准确**：准确。正确给出"进程是运行中的程序"的定义，用表格清晰对比了进程与程序的区别。

**具体分析**：5个chunk全部来自cpu-intro.pdf本章，无跨书/跨章节污染，前2个（score最低）直接支撑答案。此题此次审查未复现此前中文版本审查时观察到的Java EPUB跨书混入问题（见"遇到的问题"）。

### cs-b002

**题目**："进程的机器状态（machine state）由哪三类主要成分构成？"

**检索query**："进程的机器状态由哪三类主要成分构成"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0005/0007`（进程状态running/ready） | 0.4144 | **不能**——排名第1，但讲的是进程状态不是machine state构成，文不对题 |
| `cpu-intro.pdf/p0002/0002`（memory/registers） | 0.4186 | 能 |
| `cpu-intro.pdf/p0004/0004`（内存布局图示） | 0.4310 | 部分能 |
| `cpu-intro.pdf/p0009/0016`（ASIDE box，明确列出memory/registers/IO三项） | 0.4465 | **能，是最直接答案**，但排名倒数第2 |
| `cpu-intro.pdf/p0007/0011`（I/O追踪表） | 0.4589 | 不能 |

**回答是否准确**：准确（memory/registers/I/O三项都答对了）。

**具体分析**：答案准确是运气而非排序起作用——最直接能回答此题的chunk（`p0009/0016`）排名倒数第2，排名第1的chunk反而文不对题（讲的是进程状态生命周期，不是machine state的构成成分，两个概念在书里是分开的小节）。5个citation里有2个真正相关（第2、4名），说明即便排序不理想，多数情况下正确内容仍会挤进top-5，但这不能保证——排序质量本身是检索层的真实缺陷。

### cs-b003

**题目**："What technique does the operating system use to run multiple processes on a single physical CPU at the same time? What is its core cost?"

**检索query**："operating system technique for running multiple processes on a single CPU and its core cost"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0001/0001`（time sharing定义） | 0.3547 | **能，排名第1** |
| `cpu-sched-multi.pdf/p0001/0000`（章节介绍） | 0.3600 | 不能 |
| `cpu-sched-multi.pdf/p0002/0003`（单核多核缓存差异） | 0.3604 | 不能 |
| `cpu-sched-multi.pdf/p0002/0002`（多核调度问题引入） | 0.3641 | 不能 |
| `cpu-sched-multi.pdf/p0007/0016`（多核负载均衡） | 0.3652 | 不能 |

**回答是否准确**：准确，且直接引用了原文"This basic technique, known as time sharing of the CPU..."。

**具体分析**：英文query下目标chunk稳居第1。此题中文版本审查时曾完全检索失败（目标chunk排名第9，top-5全部被跨章节内容占据），是本轮最重要的跨语言证据，详见"遇到的问题"第1节。

### cs-b004

**题目**："OS 将程序加载为进程时，在跳转到 main() 之前会依次完成哪些初始化步骤？"

**检索query**："操作系统在将程序加载为进程时，跳转到 main() 之前的初始化步骤"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0005/0006` | 0.3503 | 能 |
| `threads-intro.pdf/p0007/0012`（gcc编译示例代码） | 0.3974 | 不能 |
| `threads-api.pdf/p0007/0032`（pthread_cond_wait） | 0.4160 | 不能 |
| `cpu-intro.pdf/p0004/0005` | 0.4174 | 能 |
| `cpu-api.pdf/p0002/0005`（fork() PID说明） | 0.4230 | 不能 |

**回答是否准确**：准确（加载代码/初始化栈/设置I/O/main()跳转均答对，堆初始化部分表述基本合理）。

**具体分析**：5个citation里3个（60%）跟本题无关，不相关的threads-api chunk（0.4160）和相关的cpu-intro chunk（0.4174）分数几乎相同，score本身分不出这两者的差异。

### cs-b005

**题目**："What are the three basic states of a process? What does each mean, and what conditions trigger transitions between them?"

**检索query**："three basic states of a process in operating systems"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0005/0007` | 0.2827 | 能 |
| `cpu-intro.pdf/p0009/0016`（ASIDE总结） | 0.3353 | 部分能 |
| `cpu-intro.pdf/p0002/0002`（machine state构成，非三状态） | 0.3456 | 不能 |
| `cpu-intro.pdf/p0001/0000`（进程定义） | 0.3542 | 不能 |
| `cpu-intro.pdf/p0005/0006`（I/O初始化） | 0.3563 | 不能 |

**回答是否准确**：准确，三种状态定义及转换条件均正确。

**具体分析**：英文版本score普遍低于中文版本同类chunk（对比中文版`p0005/0007`是0.3838），跨语言效应的又一实例。核心答案chunk排名第1，检索质量本身没问题。

### cs-b006（2026-07-20重出）

**题目**："cpu-intro.pdf 的 Figure 4.4 展示了 Process0 和 Process1 的执行追踪：两者在时间单位1同时到达系统。Process0先运行到时间单位3，随后发起I/O进入阻塞状态，I/O持续到时间单位6结束；Process1在Process0阻塞期间（从时间单位4开始）运行，到时间单位8完成。Process0在I/O结束后于时间单位9恢复运行，到时间单位10完成。请计算Process0和Process1各自的周转时间（周转时间=完成时刻-到达时刻+1，以时间单位数计）。"

**检索query**："周转时间的定义和计算公式"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0003/0008`（FIFO周转时间算例） | 0.4186 | 部分相关（演示公式用法，非本题所需的精确定义） |
| `cpu-sched.pdf/p0002/0004`（精确公式：T_turnaround = T_completion − T_arrival） | 0.4188 | **能，最直接答案** |
| `cpu-sched.pdf/p0002/0003`（引入turnaround time作为调度指标） | 0.4369 | 部分相关 |
| `cpu-sched.pdf/p0003/0010`（convoy effect算例） | 0.4383 | 不能 |
| `cpu-sched.pdf/p0007/0025`（Round-Robin介绍） | 0.4530 | 不能 |

**回答是否准确**：准确，Process0=10个时间单位、Process1=8个时间单位，与标准答案完全一致。

**具体分析**：原题（进程A/B/5ms/10ms全部是自编数字）已于本轮重出——原始版本编造的数字在书里没有任何对应词汇，检索没有锚点，属于题目设计缺陷（用户指正）。新题把Figure 4.4的真实场景数据直接写入题目本身，因此模型检索时问的是通用的"周转时间定义公式"而不是场景本身，成功检索到cpu-sched.pdf里的精确公式定义并正确套用。ground_truth已相应更新为公式chunk（`cpu-sched.pdf/p0002/0004`），不再指向cpu-intro.pdf的Figure 4.4原始chunk——题目场景仍溯源自Figure 4.4（保证内容真实性），但检索需求实际落在公式定义上。

### cs-b007（2026-07-20重出）

**题目**："Does the cpu-intro chapter discuss file system persistence mechanisms, such as how files are organized and stored on disk?"

**检索query**："file system persistence mechanisms, how files are organized and stored on disk in CPU-Intro chapter"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched-multi.pdf/p0002/0003`（硬件缓存） | 0.3847 | 不能 |
| `cpu-intro.pdf/p0004/0004`（程序加载内存示意图） | 0.3967 | 不能 |
| `cpu-sched-multi.pdf/p0001/0000`（章节介绍） | 0.3993 | 不能 |
| `cpu-sched-multi.pdf/p0003/0005` | 0.4055 | 不能 |
| `cpu-sched-multi.pdf/p0004/0007` | 0.4059 | 不能 |

**回答是否准确**：准确拒答——"The CPU-Intro chapter does not explicitly discuss file system persistence mechanisms..."，无幻觉。

**具体分析**：原题（问cpu-intro是否讨论FIFO/RR性能对比）已于本轮重出——原题检索到的第1个chunk（`cpu-sched.pdf/p0002/0006`，score=0.3218，本轮审查里最低分数之一）内容是FIFO调度的完整性能分析，真实、高相关度地回答了"书里是否讨论FIFO性能"，只是内容来自同一本书的另一章节。按判定标准，无答案题如果检索内容真能推出答案就该重出，原题不满足"无答案"前提，是题目设计缺陷不是issue #40幻觉案例。新题问的是persistence（属OSTEP原书第三部分，不在这批8个PDF+epub+音频语料范围内），5个score全部偏高（0.385~0.406），明显高于其他题"真正相关"的分数段（多在0.25~0.38），没有一个能支撑答案，模型正确拒答。

---

## 遇到的问题（跨题目共性发现）

### 1. 跨语言查询对检索分数有显著、可复现的影响

这批语料混合中英文（OSTEP 8个PDF是英文，`java-ch1-e2e.epub`是中文），测试集因此中英文各半。cpu-intro.pdf这批的中英对照实验中，同一个chunk、同一个库，仅因query语言不同产生了决定性差异：

| 对比项 | 中文query | 英文query |
|---|---|---|
| cs-b003目标chunk `p0001/0001` 排名 | 第9名（top-5未命中） | **第1名** |
| cs-b003目标chunk `p0001/0001` score | 0.3957 | 0.3547 |
| cs-b001核心chunk `p0001/0000` score | 0.3274 | 0.2615 |
| cs-b001核心chunk `p0002/0002` score | 0.3797 | 0.2950 |
| cs-b005核心chunk `p0005/0007` score | 0.3838 | 0.2827 |

中文query下，cs-b003排在目标chunk前面的全部是`cpu-sched-multi.pdf`的多核调度/缓存亲和性内容（score 0.3762~0.3824）——语义上沾"多进程共享CPU"的边，但概念上是完全不同的"多核"话题；英文query直接命中目标chunk。这不是个例，是可复现的系统性现象。

**对issue #40的启发**：单一固定cosine阈值可能需要按query语言区分对待，或者更依赖reranker（`docs/future-roadmap.md`已规划的`bge-reranker-v2-m3`，目前未实现）做二次排序，而不是指望dense embedding自己在跨语言场景下也能干净分离相关性。

### 2. 领域同质化——即使同语言，score也分不清"能答"和"不能答"

cs-b001中文版本审查阶段的完整数据：

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0001/0000` | 0.3274 | 能 |
| `cpu-intro.pdf/p0002/0002` | 0.3797 | 能 |
| `cpu-intro.pdf/p0005/0006` | 0.4065 | 不能 |
| `java-ch1-e2e.epub/p0004/0016`（Java流处理，完全无关） | 0.4126 | 不能 |
| `cpu-intro.pdf/p0005/0007` | 0.4132 | 不能 |

真正支撑答案的2个chunk（0.327/0.380）和3个不支撑的chunk（0.4065~0.4132，含完全无关的跨书Java内容）之间score差距只有约0.03，后3个彼此更是只差0.006~0.007——score本身无法作为清晰的相关性分界线。这是同一本教材内所有chunk共享领域词汇（process/CPU/memory/scheduler……）导致的效应，跟跨语言问题是两个独立成因，会叠加。此题英文版本审查时未复现Java EPUB混入，但领域同质化本身（cpu-intro内部相关/不相关chunk score挤在一起）在多道题里反复出现（见cs-b002、cs-b004）。

### 3. Reranker/BM25对上述两个问题的预期缓解程度

- **领域同质化**：reranker（cross-encoder联合编码query+document）能直接判断内容是否真正回答问题，不受"共享领域词汇"干扰，是这个问题的针对性解法；BM25仅在query用了书中精确稀有词汇（如"time sharing"）时有效，对同义改写（如"并发执行"）无效，只能部分缓解。
- **跨语言损耗**：bge-reranker-v2-m3按设计支持多语言/跨语言场景，理论上应该有帮助，但本项目尚未实测验证。BM25对跨语言场景基本无效（纯词面匹配，中英文无字面重叠），唯一例外是CS领域术语常保留英文不翻译（如"CPU"、"I/O"、"PID"），中文query若带这些词能捡到一点，但这是语料/领域特有的巧合，不是通用解法。更直接的跨语言修复方向是架构层面的query翻译（查询前先译成语料主语言），不涉及reranker/BM25。

### 4. citation排序质量与噪音比例是独立于Hit@5的隐藏问题

cs-b002、cs-b004两题按Hit@5计算都是命中（ground truth chunk确实在top-5里），但cs-b002最直接答案的chunk排名倒数第2、cs-b004检索噪音占60%——这些问题在Hit@5这个二元粗指标下完全不可见。Hit@5只要求"5个里有1个对的就算过"，不管排序质量、不管中间混了多少噪音、不管换个语言/措辞会不会直接翻车（cs-b003中文版就是活例子）。这些finding的价值在于给issue #40定阈值方案提供"现有分数体系有多脆弱"的证据，不代表当前benchmark指标本身有问题。

### 5. 全局固定dense阈值不可行的直接证据，及可能的替代路线

对比cs-b002和cs-b007（新题）的真实score，两题的"该留"和"该扔"区间是反的：

| 题目 | 内容性质 | score |
|---|---|---|
| cs-b002 `cpu-intro.pdf/p0009/0016` | 该留——最直接能回答问题的正确chunk | **0.4465** |
| cs-b007 5个citation | 该扔——全部跟"文件系统持久化"无关 | **0.3847~0.4059** |

cs-b007里"该扔"的垃圾内容，score反而比cs-b002里"该留"的正确答案更低（按余弦距离更"相关"）。不管把固定阈值设在哪个数字，要么把cs-b002的正确答案一起卡掉，要么把cs-b007的垃圾内容放进去——这不是调参能解决的，是dense余弦距离本身跨query不可比、不能当全局绝对刻度用的结构性问题。

"全局固定dense阈值"这个issue #40最初设想的方案大概率不可行，但"阈值"这个大方向不一定要放弃，留几条待后续消融实验/issue #40设计阶段验证的备选路线（这轮审查不决定用哪条，仅记录）：

1. **相对阈值**：不用绝对数字，而是跟同一次检索结果内部的最优分数比差距，每次检索自己归一化，规避跨query不可比问题
2. **阈值设在reranker分数上**：reranker是按"query+document是否相关"直接训练的分类式模型，输出分数理论上比dense距离更有跨query可比性（待reranker消融实验验证）
3. **低置信度标记，不做硬过滤**：低于阈值的不是不返回，而是标`low_confidence`，让模型在prompt里自己降低断言强度，容错空间比精确阈值分离更大
4. **不靠数值阈值，靠prompt核对来源**：system prompt强制模型核对"检索到的chunk来源文件是否等于问题所指的文件"，issue #40原文已提过这个备选方向
