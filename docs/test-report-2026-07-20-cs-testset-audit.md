# CS测试集审查+扩容：真实管线审查记录

记录审查`eval/testset/cs/qa/qa.jsonl`过程中，用真实端到端管线（`book_id=cs-eval`，`answer()`，`qwen3:q4km`）对每道题的检索质量核验结果。审查方法：`eval/audit_question.py`跑真实`answer()`，逐个citation核对`score`（ChromaDB cosine距离，越小越相关）和chunk全文是否真能推出标准答案。

格式：每题按"题号+题目原文+score表格+回答是否准确+具体分析"记录，只保留当前有效的题目和结论，不记录被替换/废弃的题目版本或已修正的错误判断；跨题目的共性问题（不针对某一道题）统一放最后"遇到的问题"一节，不为这些问题单独开GitHub issue——issue #40（retrieve无相关性阈值）本身就是冲着这类问题去的，现在暴露出的检索/幻觉现象是预期中会被后续修复的对象。

**当前管线状态**：`pipeline/agent/tools.py`（retrieve工具`query`参数说明）和`pipeline/agent/client.py`（`_SYSTEM_PROMPT`）已加入三条指导：①query优先用书中原文术语；②问题包含差异较大的子问题时应分别调用retrieve；③retrieve返回内容没回答问题时要说明未查找到相关资料。下面全部结果都是在这个状态下跑出来的。这两处改动是否保留待用户决定。

## cpu-intro.pdf 章节（Task 3，2026-07-20）

### cs-b001

**题目**："What is the operating system's precise definition of a 'process'? What is the difference between a process and a program?"

**检索query**："operating system definition of a process"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0001/0000` | 0.2595 | 能（进程定义核心段） |
| `cpu-intro.pdf/p0002/0002` | 0.3023 | 能（machine state细化，支撑"跟程序的区别"） |
| `cpu-intro.pdf/p0005/0007` | 0.3567 | 不能（进程状态running/ready，非定义/区别） |
| `cpu-intro.pdf/p0009/0016` | 0.3577 | 部分能（ASIDE总结，含定义相关内容） |
| `cpu-intro.pdf/p0003/0003` | 0.3713 | 不能（进程API总览Create/Destroy/Wait） |

**回答是否准确**：准确，定义+对比表格均正确。

**具体分析**：5个chunk全部来自cpu-intro.pdf本章，无跨书/跨章节污染。

### cs-b002

**题目**："进程的机器状态（machine state）由哪三类主要成分构成？"

**检索query**："进程的机器状态（machine state）由哪三类主要成分构成"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0005/0007`（进程状态running/ready） | 0.4112 | **不能**——排名第1，但讲的是进程状态不是machine state构成，文不对题 |
| `cpu-intro.pdf/p0002/0002`（memory/registers） | 0.4214 | 能 |
| `cpu-intro.pdf/p0009/0016`（ASIDE box，明确列出memory/registers/IO三项） | 0.4494 | **能，是最直接答案**，但排名第3 |
| `cpu-intro.pdf/p0004/0004`（内存布局图示） | 0.4596 | 部分能 |
| `cpu-intro.pdf/p0007/0011`（I/O追踪表） | 0.4687 | 不能 |

**回答是否准确**：准确（memory/registers/I/O三项都答对了）。

**具体分析**：最直接能回答此题的chunk（`p0009/0016`）排名第3而非第1，排名第1的chunk反而文不对题——检索排序有缺陷。答案最终准确的具体原因未验证（可能是模型综合了`p0002/0002`/`p0009/0016`等有用chunk，也可能这类常见OS知识点模型训练时已掌握、检索内容未起决定作用，两种可能没有证据区分）。可以确定的是排序缺陷本身真实存在：如果后续接入更严格的top-k截断或阈值/reranker把`p0009/0016`过滤掉，检索质量会比这次实际观察到的更差。

### cs-b003

**题目**："What technique does the operating system use to run multiple processes on a single physical CPU at the same time? What is its core cost?"

**检索query**："operating system technique for running multiple processes on a single physical CPU at the same time and its core cost"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0001/0001`（time sharing定义） | 0.3307 | **能，排名第1** |
| `cpu-sched-multi.pdf/p0002/0003`（单核多核缓存差异） | 0.3545 | 不能 |
| `cpu-sched-multi.pdf/p0001/0000`（章节介绍） | 0.3600 | 不能 |
| `cpu-sched-multi.pdf/p0005/0010`（cache affinity） | 0.3643 | 不能 |
| `cpu-sched-multi.pdf/p0002/0002`（多核调度问题引入） | 0.3645 | 不能 |

**回答是否准确**：准确，直接引用了原文"This basic technique, known as time sharing of the CPU..."。

**具体分析**：英文query下目标chunk稳定排名第1。同一问题若改用中文提问（如"操作系统如何在单个物理CPU上实现多个进程的并发执行"），目标chunk会跌到第9名、完全跌出top-5，被语义相邻但概念不同的`cpu-sched-multi.pdf`多核调度内容压过——跨语言检索损耗是真实、可复现的现象，详见"遇到的问题"第1条。

### cs-b004

**题目**："OS 将程序加载为进程时，在跳转到 main() 之前会依次完成哪些初始化步骤？"

**检索query**："操作系统在将程序加载为进程时，在跳转到 main() 之前会依次完成哪些初始化步骤"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0005/0006` | 0.3040 | 能 |
| `cpu-intro.pdf/p0004/0005` | 0.3851 | 能 |
| `threads-intro.pdf/p0007/0012`（gcc编译示例代码） | 0.4054 | 不能 |
| `threads-api.pdf/p0007/0032`（pthread_cond_wait） | 0.4103 | 不能 |
| `threads-intro.pdf/p0004/0006`（pthread_join示例） | 0.4152 | 不能 |

**回答是否准确**：准确（加载代码/初始化栈/设置I/O/main()跳转均答对，堆初始化部分表述基本合理）。

**具体分析**：两个真正相关的chunk排名第1、第2，紧挨在一起，但5个citation里仍有3个（60%）跟本题无关。

### cs-b005

**题目**："What are the three basic states of a process? What does each mean, and what conditions trigger transitions between them?"

**检索query**："three basic states of a process and their meanings and transition conditions"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-intro.pdf/p0005/0007`（三状态定义） | 0.3582 | 能 |
| `cpu-intro.pdf/p0006/0008`（Figure 4.2状态转换图，含Scheduled/Descheduled/I/O标签） | 0.4207 | 能 |
| `cpu-intro.pdf/p0006/0009`（Blocked状态定义+转换描述） | 0.4509 | 能 |
| `cpu-intro.pdf/p0006/0010`（Figure 4.3追踪表，无I/O版本） | 0.4543 | 部分能 |
| `cpu-intro.pdf/p0001/0000`（进程定义，非状态） | 0.4567 | 不能 |

**回答是否准确**：准确，三种状态定义及转换条件均正确。

**具体分析**：5个chunk里4个真正讲状态/转换，检索质量良好，无跨书/跨章节污染。

### cs-b006

**题目**："cpu-intro.pdf 的 Figure 4.4 展示了 Process0 和 Process1 的执行追踪：两者在时间单位1同时到达系统。Process0先运行到时间单位3，随后发起I/O进入阻塞状态，I/O持续到时间单位6结束；Process1在Process0阻塞期间（从时间单位4开始）运行，到时间单位8完成。Process0在I/O结束后于时间单位9恢复运行，到时间单位10完成。请计算Process0和Process1各自的周转时间（周转时间=完成时刻-到达时刻+1，以时间单位数计）。"

**检索query**："周转时间的定义"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0002/0004`（精确公式：T_turnaround = T_completion − T_arrival） | 0.4564 | **能，最直接答案，排第1** |
| `cpu-sched.pdf/p0002/0003`（引入turnaround time作为调度指标） | 0.4672 | 部分相关 |
| `cpu-sched.pdf/p0003/0010`（convoy effect算例） | 0.4679 | 不能 |
| `cpu-sched.pdf/p0002/0005`（turnaround作为性能指标的说明） | 0.4835 | 部分相关 |
| `cpu-sched.pdf/p0003/0008`（FIFO周转时间算例） | 0.4893 | 部分相关 |

**回答是否准确**：准确，Process0=10个时间单位、Process1=8个时间单位，与标准答案完全一致，回答里还主动指出题目给的公式"完成-到达+1"跟书里标准公式"完成-到达"略有出入，并遵循题目给的口径计算，处理得当。

**具体分析**：题目场景直接取自Figure 4.4的真实追踪数据（而非编造数字），检索到的是通用的周转时间公式定义并正确应用。ground_truth对应`cpu-sched.pdf/p0002/0004`这个公式chunk。

### cs-b007

**题目**："Does the cpu-intro chapter discuss file system persistence mechanisms, such as how files are organized and stored on disk?"

**检索query**："file system persistence mechanisms, how files are organized and stored on disk"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0012/0029`（提到file system用journaling/copy-on-write，但在讲并发原子性） | 0.4463 | 不能 |
| `cpu-intro.pdf/p0007/0013`（进程列表数据结构） | 0.4588 | 不能 |
| `cpu-intro.pdf/p0008/0015`（进程状态寄存器保存） | 0.4662 | 不能 |
| `vm-segmentation.pdf/p0009/0026`（外部碎片管理） | 0.4754 | 不能 |
| `vm-segmentation.pdf/p0010/0027`（空闲空间分配算法） | 0.4771 | 不能 |

**回答是否准确**：准确拒答，且处理得比较精细——"there is a mention of file systems using journaling or copy-on-write... but this appears in a different chapter related to concurrency rather than CPU internals"，正确识别出`threads-intro.pdf`里提到的journaling/copy-on-write不属于cpu-intro章节，没有把跨章节内容误归因。

**具体分析**：persistence属于OSTEP原书第三部分，不在这批语料范围内，5个score全部偏高（0.446~0.477），明显高于其他题"真正相关"的分数段（多在0.25~0.40），没有一个能支撑答案，模型正确拒答。

---

## cpu-api.pdf 章节（Task 4，2026-07-20）

### cs-b008

**题目**："What value does fork() return in the parent process versus the child process? What does it return if the call fails?"

**检索query**："fork system call return values for parent, child, and failure cases"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0003/0007`（父进程收到PID，子进程收到0） | 0.3680 | 能（父子返回值部分） |
| `cpu-api.pdf/p0002/0002`（Figure 5.1代码，含`if (rc < 0)`失败分支） | 0.4128 | 部分能（代码隐含失败返回负值，但没有明确写"-1"） |
| `cpu-api.pdf/p0014/0034`（练习题） | 0.4191 | 不能 |
| `cpu-api.pdf/p0010/0027`（fork API总结） | 0.4204 | 部分能 |
| `cpu-api.pdf/p0005/0017`（exec()内容，非fork） | 0.4264 | 不能 |

**回答是否准确**：准确，回答表述为"If the call fails, fork() returns a value **less than 0**"，跟检索内容实际能支撑的结论范围一致（代码里`if(rc<0)`隐含负值，但没有明确写"-1"这个具体数值，回答也没有超出这个范围去断言）。

**具体分析**：核心chunk排名第1，检索质量正常。

### cs-b009

**题目**："exec() 系列调用成功执行后为什么不会返回到调用它的代码？"

**检索query**："exec() 系列函数在操作系统中的行为特点，为什么执行后不会返回到调用它的代码"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0005/0017`（exec()替换代码段行为） | 0.3821 | 能，排名第1 |
| `java-ch1-e2e.epub/p0006/0066`（讲嵌套控制流难懂，完全无关） | 0.3875 | 不能 |
| `cpu-api.pdf/p0004/0013`（exec()整体介绍） | 0.3930 | 部分能 |
| `cpu-api.pdf/p0006/0018`（fork/exec分离原因） | 0.4066 | 部分能 |
| `threads-intro.pdf/p0009/0015`（多线程结果不确定性，无关） | 0.4133 | 不能 |

**回答是否准确**：准确，正确解释了exec()替换地址空间导致不返回的机制。

**具体分析**：跨书Java EPUB无关内容混入citation第2名（score=0.3875，跟真正相关内容0.3821几乎无法区分），是"cs"库混合多学科语料后会反复出现的真实场景，详见"遇到的问题"第3条。

### cs-b010

**题目**："What does wait() do? What happens if the parent process doesn't call wait() and the child process exits first?"

**检索query**："what does the wait() system call do in Unix-like operating systems, and what happens if the parent process doesn't call wait() when the child process exits"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0004/0010`（wait()阻塞机制） | 0.2557 | 能（wait()作用部分） |
| `cpu-api.pdf/p0010/0027`（fork API总结） | 0.3163 | 不能 |
| `cpu-api.pdf/p0004/0013`（exec()介绍） | 0.3228 | 不能 |
| `cpu-api.pdf/p0014/0034`（练习题） | 0.3474 | 不能 |
| `cpu-api.pdf/p0004/0012`（wait()具体例子） | 0.3633 | 部分能 |

**回答是否准确**：准确——正确描述了僵尸进程（zombie）机制、进程表项不释放的现象，但完全靠模型训练知识补足，检索到的5个chunk没有一个提到zombie。

**具体分析**：题目原文（中英文都一样）全程没有出现"僵尸/zombie"这个词，只描述了"父进程不调用wait()、子进程先退出"这个场景。retrieve的query由模型从题目原文生成，没有"zombie"这个锚点，检索找不到僵尸进程定义所在的chunk（`cpu-intro.pdf/p0009/0016`，用精确英文query单独核实过，内容确实存在，score=0.3841排全库第1）。这是"单次query-from-question的检索机制，对只描述场景、不给术语的问题"存在的真实结构性局限，不是简单的"该检索到的没检索到"式检索bug，也不是题目本身出得不好——真实用户提问经常就是这样描述场景而不给教科书术语，是有代表性的产品场景。ground_truth已更新为两个chunk（`cpu-api.pdf/p0004/0010`+`cpu-intro.pdf/p0009/0016`）。详见"遇到的问题"第7条。

### cs-b011

**题目**："fork() 后子进程是否会获得父进程文件描述符的独立副本？这一特性如何支撑 shell 的输出重定向功能？"

**检索query**："fork() 系统调用后，子进程是否继承父进程的文件描述符？以及该机制如何支持 shell 的输出重定向功能"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0003/0007`（fork基本机制） | 0.3701 | 部分能 |
| `cpu-api.pdf/p0007/0022`（重定向具体例子+pipe机制） | 0.3861 | 能 |
| `cpu-api.pdf/p0006/0020`（重定向机制，fd在exec()后保持打开） | 0.3881 | 能 |
| `cpu-api.pdf/p0002/0005`（PID/fork基本概念，非fd） | 0.3912 | 不能 |
| `cpu-api.pdf/p0014/0034`（练习题） | 0.3939 | 部分能 |

**回答是否准确**：准确，完整解释了fd继承机制+shell重定向实现原理。

**具体分析**：检索质量正常，5个chunk全部来自本章，核心内容直接支撑答案，无跨书/跨章节污染。

### cs-b012

**题目**："shell 执行用户输入命令的典型三步流程是什么？"

**检索query**："shell 执行用户输入命令的典型三步流程"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `java-ch1-e2e.epub/p0004/0019`（Unix管道图示，Java书内容，无关） | **0.3895** | **不能，排名第1** |
| `cpu-api.pdf/p0006/0018`（明确讲fork→exec→wait三步） | 0.3926 | 能 |
| `cpu-api.pdf/p0005/0014`（代码示例演示三步） | 0.3977 | 部分能 |
| `cpu-intro.pdf/p0005/0006`（进程初始化I/O设置，非shell流程） | 0.3990 | 不能 |
| `cpu-api.pdf/p0006/0020`（重定向细节） | 0.4088 | 部分能 |

**回答是否准确**：基本准确（fork/重定向/exec+wait三步都对），但回答开头加了标准答案没有的"①解析与分词（Parsing and Tokenization）"这一步，检索到的5个chunk里也没有任何内容提到"分词"，这部分是模型自行补充的、未经检索验证的细节。

**具体分析**：跨书Java EPUB内容排名第1，是本轮观察到的同一模式的又一实例（另见cs-b009），详见"遇到的问题"第3条。

### cs-b013

**题目**："How many lines of \"hello\" will the following C code print in total when executed?\nint main() { fork(); fork(); printf(\"hello\\n\"); return 0; }"

**检索query**："C language fork system call behavior and how it affects program execution tree"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0005/0017`（exec()内容） | 0.3312 | 不能 |
| `cpu-api.pdf/p0013/0031`（fork.py模拟器练习题） | 0.3805 | 部分能 |
| `cpu-api.pdf/p0001/0001`（fork()基本介绍） | 0.3836 | 部分能 |
| `cpu-api.pdf/p0006/0018`（shell fork/exec分离） | 0.3927 | 不能 |
| `cpu-api.pdf/p0014/0034`（练习题） | 0.4037 | 不能 |

**回答是否准确**：最终答案正确（4行），但生成过程不稳定。独立测试4次，2次直接给出简洁正确的"4 times"，2次开头先给错误答案（一次"three times"、一次"seven times"），中间反复出现"But wait"、"let me re-examine/correct my reasoning"式的自我怀疑循环，最终仍收敛到正确的"4 times"。

**具体分析**：检索到的都是fork()基础介绍性内容，没有一个chunk真正展示"嵌套fork调用树"这种具体分析方法，这道题本质上主要靠推理而非检索，4次测试的citation内容大体一致，问题不在检索。生成过程约一半概率出现开头给错、中途自我纠正的模式，是真实、可复现观察到的现象；具体技术成因未验证（`OllamaAgentClient`确实按`temperature=0.0`把参数传给了API，但传了`temperature=0`不代表输出必然确定性一致，中间的具体机制没有深挖，不应断言是某个具体原因）。这跟检索质量无关，是生成环节的问题，不在issue #40范畴，记录供后续参考。

### cs-b014

**题目**："多个用 fork() 创建的兄弟进程之间，操作系统提供了信号量（semaphore）这类同步原语来协调彼此的执行顺序吗？具体是怎么用的？"（出题前先用`semaphore`关键词查过全库文档原文，确认0次出现）

**检索query**（触发了2次retrieve）：
1. "在多进程环境下，fork()创建的兄弟进程如何使用信号量（semaphore）进行同步？"
2. "信号量（semaphore）在多进程同步中的作用和使用方法"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0013/0030`（fork.py模拟器介绍） | 0.4508 | 不能 |
| `cpu-api.pdf/p0010/0027`（fork API总结） | 0.4685 | 不能 |
| `cpu-api.pdf/p0003/0007`（fork父子返回值） | 0.4746 | 不能 |
| `threads-intro.pdf/p0013/0035`（同步原语需要什么硬件/OS支持，概念性提问不是semaphore具体内容） | 0.4801 | 不能 |
| `cpu-api.pdf/p0002/0005`（PID/fork基本概念） | 0.4851 | 不能 |
| `cpu-sched-multi.pdf/p0013/0036`（cache affinity练习题） | 0.4736 | 不能 |
| `cpu-sched-multi.pdf/p0012/0034`（多核调度模拟器练习题） | 0.4864 | 不能 |
| `cpu-sched-multi.pdf/p0013/0037`（per-CPU调度练习题） | 0.4882 | 不能 |
| `threads-api.pdf/p0008/0041`（条件变量使用建议，不是semaphore） | 0.4908 | 不能 |
| `threads-intro.pdf/p0013/0035`（同上，第2次检索重复命中） | 0.4924 | 不能 |

**回答是否准确：不准确，严重幻觉**。两次retrieve共10个chunk，没有一个提到semaphore，但模型给出了一整套详细、自信的POSIX信号量使用教程——`sem_init`初始化、`sem_wait`/`sem_post`的具体调用方式、一个"三个子进程按顺序执行"的示例场景、"避免竞争条件"的注意事项——全部是训练知识编造，检索内容完全没有提供任何依据。回答末尾仍被自动挂上10个citation的引用标签，看起来像是有真实依据支撑的。system prompt里"retrieve返回内容没回答问题时要说明未查找到相关资料"这条指令完全没有被触发。

**具体分析**：语料库里真实没有semaphore内容（10个score都在0.45~0.49，明显高于其他题"真正相关"的分数段），题目设计本身没有问题。这是本轮审查目前最严重的issue #40幻觉实例——检索内容完全不相关，模型仍然编出一套具体、自信、带伪代码级细节的错误知识，且现有prompt指令拦不住。详见"遇到的问题"第6条。

---

## 遇到的问题（跨题目共性发现）

### 1. 跨语言查询对检索分数有显著、可复现的影响

这批语料混合中英文（OSTEP 8个PDF是英文，`java-ch1-e2e.epub`是中文），测试集因此中英文各半。cs-b003是最直接的证据：同一个目标chunk（`cpu-intro.pdf/p0001/0001`，含"time sharing"定义），中文query排名第9（完全没进top-5），英文query稳定排名第1。中文query下，排在目标chunk前面的全部是`cpu-sched-multi.pdf`的多核调度/缓存亲和性内容——语义上沾"多进程共享CPU"的边，但概念上是完全不同的"多核"话题。cs-b001、cs-b005同样观察到英文版核心chunk的score系统性低于中文版同类chunk。

**结论**：中文query查英文原文存在真实、可复现的跨语言检索损耗，不是随机噪音。这既是bge-m3多语言对齐能力的固有特性，也说明当前语料的领域同质化（见下）会在跨语言场景下被放大。对issue #40的启发：单一固定cosine阈值可能需要按query语言区分对待，或者更依赖reranker做二次排序。

### 2. 领域同质化——即使同语言，score也分不清"能答"和"不能答"

cs-b002、cs-b004反复出现"最相关的chunk排名不是第一"这类排序质量问题，真正相关和不相关的chunk之间score差距经常只有0.01~0.03，本身无法作为清晰的相关性分界线。这是同一本教材内所有chunk共享领域词汇（process/CPU/memory/scheduler……）导致的效应，跟跨语言问题是两个独立成因，会叠加。

### 3. 跨书内容混入citation是可复现的模式，不是偶发

cs-b009、cs-b012都观察到`java-ch1-e2e.epub`的无关内容排到citation第1、2名，score跟真正相关内容几乎无法区分。原因：Java和OSTEP虽然是两本完全不同的书，但都是编程/CS领域的技术文本，会大量出现"进程"、"程序"、"数据"、"内存"这类共同词汇，embedding算出来的向量因此天然靠得比较近。这是独立于"跨语言"和"同书同质化"之外的第三个成因，三者会叠加。

### 4. Reranker/BM25对上述问题的预期缓解程度

- **领域同质化/跨书污染**：reranker（cross-encoder联合编码query+document）能直接判断内容是否真正回答问题，不受"共享领域词汇"干扰，是针对性解法；BM25仅在query用了书中精确稀有词汇时有效，对同义改写无效，只能部分缓解。
- **跨语言损耗**：bge-reranker-v2-m3按设计支持多语言/跨语言场景，理论上应该有帮助，但本项目尚未实测验证。BM25对跨语言场景基本无效（纯词面匹配，中英文无字面重叠），唯一例外是CS领域术语常保留英文不翻译（如"CPU"、"I/O"、"PID"），中文query若带这些词能捡到一点，但这是语料/领域特有的巧合，不是通用解法。更直接的跨语言修复方向是架构层面的query翻译，不涉及reranker/BM25。

### 5. 全局固定dense阈值不可行的直接证据，及可能的替代路线

对比cs-b002和cs-b007的真实score，两题的"该留"和"该扔"区间几乎完全重叠：

| 题目 | 内容性质 | score |
|---|---|---|
| cs-b002 `cpu-intro.pdf/p0009/0016` | 该留——最直接能回答问题的正确chunk | **0.4494** |
| cs-b007 5个citation | 该扔——全部跟"文件系统持久化"无关 | **0.446~0.477** |

不管把固定阈值设在哪个数字，要么把cs-b002的正确答案一起卡掉，要么把cs-b007的垃圾内容放进去——这不是调参能解决的，是dense余弦距离本身跨query不可比、不能当全局绝对刻度用的结构性问题。

"全局固定dense阈值"这个issue #40最初设想的方案大概率不可行，但"阈值"这个大方向不一定要放弃，留几条待后续消融实验/issue #40设计阶段验证的备选路线（这轮审查不决定用哪条，仅记录）：

1. **相对阈值**：不用绝对数字，而是跟同一次检索结果内部的最优分数比差距，每次检索自己归一化，规避跨query不可比问题
2. **阈值设在reranker分数上**：reranker是按"query+document是否相关"直接训练的分类式模型，输出分数理论上比dense距离更有跨query可比性（待reranker消融实验验证）
3. **低置信度标记，不做硬过滤**：低于阈值的不是不返回，而是标`low_confidence`，让模型在prompt里自己降低断言强度，容错空间比精确阈值分离更大
4. **不靠数值阈值，靠prompt核对来源**：system prompt强制模型核对"检索到的chunk来源文件是否等于问题所指的文件"，issue #40原文已提过这个备选方向

### 6. Prompt工程能改善检索排序，但拦不住"自信编造"类幻觉

当前system prompt已加入"retrieve返回内容没回答问题时要说明未查找到相关资料"这条指令，但cs-b014证明这条指令对模型自身有强训练知识、根本不觉得"自己不知道"的专业内容（semaphore）完全不起作用——两次retrieve都查不到相关内容，模型依然自信编造一整套教程，没有触发这条指令。这说明检索排序类问题（citation噪音、排名不理想）和"自信编造"类幻觉是两类不同性质的问题：前者能通过改进检索环节本身缓解，后者的根源是模型没有意识到自己在编，不是缺一句提醒，需要issue #40真正的机制（阈值/reranker/低置信度标记），prompt工程这条路走不通。

### 7. 单跳检索对"只描述场景、不给术语"的问题存在真实结构性局限

cs-b010是代表案例：题目原文全程没有出现"zombie"这个词，只描述了"父进程不调用wait()、子进程先退出"的场景。retrieve的query由模型从题目原文生成，没有"zombie"这个锚点，检索自然找不到僵尸进程定义所在的chunk（内容确实存在于语料库里，用精确术语查得到）。这不是"该检索到的没检索到"这种干净的检索bug，也不是题目设计缺陷，而是"单次query-from-question的检索机制，对不给术语只描述场景的问题"天然覆盖不到——这类问题在真实用户场景里很常见（用户经常不知道教科书术语，只会描述现象），是有代表性的测试场景，应作为issue #40设计时的真实案例保留。
