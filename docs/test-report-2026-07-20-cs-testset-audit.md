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

**回答是否准确**：准确，Process0=10个时间单位、Process1=8个时间单位，与标准答案完全一致，回答里还主动指出题目给的公式"完成-到达+1"跟书里标准公式"完成-到达"略有出入，并遵循题目给的口径计算，处理得当。**没有调用calculate工具**，纯文本推理完成10-1+1、8-1+1这类个位数加减法。

**具体分析**：题目场景直接取自Figure 4.4的真实追踪数据（而非编造数字），检索到的是通用的周转时间公式定义并正确应用。ground_truth对应`cpu-sched.pdf/p0002/0004`这个公式chunk。这道题原先归类为计算题，但数值推导过于简单（个位数加减法），够不上"计算题"这个分类的门槛，已改判事实题；system prompt里"任何数值计算都必须调用calculate"这条规则对这种量级的算术要求本身也不合理，不能算这道题的问题。

### cs-b007

**题目**："How does the operating system give a group of processes their own isolated view of the filesystem and network, the way container runtimes like Docker do?"

**检索query**（触发4次retrieve，从不同角度尝试）：
1. "how does an operating system provide isolated filesystem and network views for processes, similar to Docker containers"
2. "how does Linux use namespaces and cgroups to isolate processes for containerization, like Docker"
3. "what are Linux namespaces and how do they provide isolated views of the filesystem and network for processes"
4. "what are Linux cgroups and how do they provide resource isolation for processes in containers"

**回答是否准确**：正确处理。4次检索全部未能返回充分相关的内容（`container`/`cgroup`/`namespace`/`Docker`/`chroot`在全库0命中），最终0个citation，模型基于自己的通用知识介绍了namespace/cgroup机制，并在回答末尾明确声明"If you're asking about a specific textbook or OS implementation... this is a general explanation based on standard operating system principles"——清楚说明这不是书里的内容，系统正确挂上`[未找到参考资料]`标签。

**具体分析**：这是本轮审查里处理得最好的无答案题案例——模型没有把"检索不到"当成"答不出来就算了"，反而多次换角度检索（4次，本轮单题最多），确认真的找不到后，坦诚说明这是通用知识而非书本依据。跟cs-b014、cs-b023的幻觉形成鲜明对比，说明这条正确行为路径是模型能力范围内可以做到的，只是不稳定。

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

## cpu-sched.pdf 章节（Task 5，2026-07-20）

### cs-b015

**题目**："In scheduling, what is the formula for calculating 'turnaround time'?"

**检索query**："turnaround time formula in scheduling"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0002/0004`（精确公式） | 0.3188 | 能，排第1 |
| `cpu-sched.pdf/p0002/0005` | 0.3325 | 部分能 |
| `cpu-sched.pdf/p0003/0008`（算例） | 0.3502 | 部分能 |
| `cpu-sched.pdf/p0002/0003`（turnaround定义） | 0.3523 | 能 |
| `cpu-sched.pdf/p0003/0010`（convoy effect） | 0.3554 | 不能 |

**回答是否准确**：准确，公式完全正确。

**具体分析**：5个chunk全部来自cpu-sched.pdf本章，检索质量正常。

### cs-b016

**题目**："FIFO 调度在什么情况下会产生「护航效应」（convoy effect）？"

**检索query**："FIFO 调度中的 convoy effect 定义和产生条件"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0003/0010`（convoy effect算例，100秒长任务） | 0.5242 | 能 |
| `cpu-sched.pdf/p0012/0034`（参考文献列表，含Convoy Phenomenon引用） | 0.5458 | 部分能 |
| `cpu-sched.pdf/p0002/0006`（FIFO介绍） | 0.5493 | 部分能 |
| `cpu-sched.pdf/p0005/0015`（convoy效应数值延续） | 0.5756 | 能 |
| `threads-intro.pdf/p0011/0028`（竞态条件，与convoy effect无关） | 0.5887 | 不能 |

**回答是否准确**：准确，正确解释了长任务阻塞短任务导致护航效应的机制。

**具体分析**：这批score普遍偏高（0.52~0.59），比其他题目的"真正相关"分数段（多在0.25~0.40）高出一截，但4/5 chunk仍然真实相关——这说明score的绝对数值不仅跨query不可比（"遇到的问题"第5条已用cs-b002/cs-b007证明过），同一批"相关"内容本身的score基准也会因题目不同而系统性偏移，进一步印证不能用固定阈值卡数值。跨章节的threads-intro内容混入citation第5名，是"遇到的问题"第3条模式的又一实例。

### cs-b017

**题目**："Why is SJF (Shortest Job First) difficult to apply directly in real systems?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0004/0011`（SJF定义） | 0.3239 | 能 |
| `cpu-sched.pdf/p0006/0018`（STCF/抢占） | 0.3866 | 部分能 |
| `cpu-sched.pdf/p0003/0010`（convoy effect） | 0.3948 | 部分能 |
| `cpu-sched.pdf/p0010/0032`（调度器不知道任务长度） | 0.4343 | 能，核心论据 |
| `cpu-sched.pdf/p0004/0013`（SJF算例） | 0.4399 | 部分能 |

**回答是否准确**：准确，核心论据（无法预知任务长度）正确，回答还补充了非抢占/护航效应等合理的延伸说明。

**具体分析**：5个chunk全部来自本章，检索质量正常。

### cs-b018

**题目**："STCF 与 SJF 的主要区别是什么？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0006/0018`（STCF定义，明确对比抢占/非抢占） | 0.3926 | 能，核心论据 |
| `cpu-sched.pdf/p0004/0013`（SJF算例） | 0.4723 | 部分能 |
| `cpu-sched.pdf/p0004/0011`（SJF定义） | 0.4889 | 能 |
| `cpu-sched.pdf/p0007/0024`（响应时间讨论） | 0.5099 | 不能 |
| `cpu-sched.pdf/p0010/0032`（调度器不知道任务长度） | 0.5385 | 不能 |

**回答是否准确**：准确，正确抓住"是否支持抢占"这个核心区别。

**具体分析**：核心论据chunk排名第1，检索质量正常。

### cs-b019

**题目**："Why does Round Robin scheduling improve response time but usually result in worse turnaround time?"

**检索query**："Round Robin scheduling and its effect on response time and turnaround time"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0007/0025`（RR定义/time slice） | 0.3387 | 能 |
| `cpu-sched.pdf/p0003/0010`（convoy effect） | 0.3458 | 不能 |
| `cpu-sched.pdf/p0008/0026`（time slice权衡讨论） | 0.3483 | 能 |
| `cpu-sched-multi.pdf/p0008/0017`（多核RR调度示例） | 0.3518 | 不能 |
| `cpu-sched.pdf/p0002/0005`（turnaround定义） | 0.3631 | 部分能 |

**回答是否准确**：核心结论准确（RR改善响应时间、牺牲周转时间），但推导过程中出现数字混淆——回答里"This is much worse than SJF's 10-second average turnaround time ($\frac{100+110+120}{3}=110$ for a different example, but in the same context...)"这句话把两个不同算例的数字混在一起，读起来前后矛盾（先说"10秒"又算出"110"）。

**具体分析**：检索到跨章节的cpu-sched-multi.pdf多核调度示例，跟本题讨论的单核RR响应时间/周转时间权衡关系不大。回答里的数字混淆是生成环节把书中RR示例（A/B/C各5秒）和另一处FIFO/convoy示例（A=100秒/B=C=10秒）的数字揉在一句话里，不是检索内容本身的错误。

### cs-b020

**题目**："调度器在处理含 I/O 的任务时，如何实现 CPU 与 I/O 的重叠利用？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0010/0031`（STCF子任务拆分实现重叠） | 0.3701 | 能，核心论据 |
| `cpu-sched.pdf/p0009/0028`（I/O阻塞决策） | 0.3910 | 能 |
| `cpu-intro.pdf/p0007/0011`（Figure 4.4 I/O重叠追踪表） | 0.4036 | 能，具体例证 |
| `cpu-intro.pdf/p0001/0001`（time sharing介绍） | 0.4036 | 部分能 |
| `cpu-intro.pdf/p0007/0012`（Figure 4.4文字说明） | 0.4059 | 能，具体例证 |

**回答是否准确**：准确，正确描述了CPU突发拆分+I/O阻塞时切换+中断恢复的完整机制。

**具体分析**：跨章节引用cpu-intro.pdf的Figure 4.4 I/O重叠追踪表是合理的——CPU/I/O重叠这个概念本身就是cpu-intro先引入、cpu-sched再用STCF子任务拆分具体实现，5个chunk全部真实相关，检索质量良好。

### cs-b021

**题目**："Three tasks A(5ms), B(10ms), and C(15ms) all arrive at t=0. Under FIFO scheduling in the order A→B→C, what is the average turnaround time?"

**检索query**："FIFO scheduling algorithm definition and how to calculate turnaround time"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0002/0006`（FIFO介绍+算例） | 0.2999 | 能 |
| `cpu-sched.pdf/p0003/0008`（周转时间算例） | 0.3280 | 能 |
| `cpu-sched.pdf/p0013/0037`（练习题） | 0.3970 | 不能 |
| `cpu-sched.pdf/p0003/0010`（convoy effect） | 0.4188 | 不能 |
| `cpu-sched.pdf/p0007/0025`（RR介绍） | 0.4297 | 不能 |

**回答是否准确**：准确，16.67ms，用了计算工具，过程清晰无矛盾。

**具体分析**：核心chunk排名前2，检索质量正常，生成过程稳定。

### cs-b022（重出，改为独立题目）

**题目**："三个任务 A(20ms)、B(5ms)、C(10ms) 同时在 t=0 到达，用 SJF（最短作业优先）调度，平均周转时间是多少？"

**检索query**："SJF 调度算法的定义和平均周转时间计算方法"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0004/0013`（SJF算例） | 0.3645 | 能 |
| `cpu-sched.pdf/p0003/0010`（convoy effect） | 0.3923 | 不能 |
| `cpu-sched.pdf/p0006/0018`（STCF/抢占） | 0.3935 | 部分能 |
| `cpu-sched.pdf/p0004/0011`（SJF定义） | 0.4244 | 能 |
| `cpu-sched.pdf/p0007/0025`（RR介绍） | 0.4277 | 不能 |

**回答是否准确**：调度顺序（B→C→A）和每个任务的周转时间（B=5ms、C=15ms、A=35ms）全部算对，但最后一步**漏除以3**——"(5+15+35)/3 = **55ms**"，正确答案应为55/3≈18.33ms。调用了calculate工具，但错误出在工具调用后的结果整合环节，不是工具本身算错。

**具体分析**：原题"同上三个任务...改用SJF调度"依赖cs-b021的上下文，但`audit_question.py`每次调用都是`history=[]`单轮独立测试，这种依赖上一轮语境的设计在当前审查方法论下根本没被真正测到——哪怕题目括号里补了具体数字使其"看起来"能独立回答，也不是这道题当初想验证的东西（多轮对话记忆）。已重出为完全独立的SJF算例，跟cs-b021互不依赖。检索质量正常，生成过程本身稳定（这次没有出现自我怀疑循环），但暴露了一个新问题：计算步骤分解正确、单步计算也调用了工具，最后汇总平均值这一步却漏掉了除法，记入"遇到的问题"第8条。

### cs-b023（重出两次，避开"这章讨论了X吗"模板）

**题目**："多级反馈队列调度算法具体是怎么根据进程的历史行为动态调整它所在的队列优先级的？"（出题前已核实`MLFQ`/`feedback queue`/`Multi-Level Feedback`语料库里只有一处一笔带过的类比提及，没有展开讲解）

**检索query**："多级反馈队列调度算法中，如何根据进程的历史行为动态调整其所在队列的优先级"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched.pdf/p0011/0033`（明确写"multi-level feedback queue...is the topic of the **next chapter**"，即不在本次语料范围内） | 0.4261 | **不能，且明确标注MLFQ在下一章** |
| `cpu-sched-multi.pdf/p0008/0021`（多核RR调度示例） | 0.4320 | 不能 |
| `cpu-sched-multi.pdf/p0005/0009`（链表加锁示例） | 0.4457 | 不能 |
| `cpu-sched-multi.pdf/p0008/0019`（调度队列示例Q0/Q1） | 0.4542 | 不能 |
| `java-ch1-e2e.epub/p0006/0065`（Java Stream API代码，完全无关） | 0.4573 | 不能 |

**回答是否准确：不准确，幻觉**。回答给出了一套具体的MLFQ规则——初始进最高优先级队列、时间片用完或阻塞则降级、长时间等待可升级、根据CPU使用率/阻塞次数/I/O频率动态调整——内容大方向不算离谱（是MLFQ真实机制的合理近似），但检索到的5个chunk没有一个实际讲解这些规则，其中排名第1的chunk原文明确写着"multi-level feedback queue...is the topic of the next chapter"——这是一个比"内容不相关"更强烈的信号，相当于书本身告诉模型"这个话题我这里不讲，下一章才讲"，模型仍然视而不见地给出了详细答案。

**具体分析**：这题第一版用"是否讨论了X"的模板句式（针对EDF），被指出这种明着问"书/章节是否讨论了某内容"的模板本身就该弃用，不管换什么话题都不该再用这个句式；重出后改成不点名pdf/章节、直接问"具体怎么实现"的自然技术问句。这次抓到的幻觉比EDF那版更明确——检索结果里甚至包含"这是下一章内容"的显式声明，模型仍然忽略这个信号给出了编造的具体规则，是本轮除cs-b014外最清晰的"忽略明确的'找不到'信号仍然作答"的案例。

---

## cpu-sched-multi.pdf 章节（Task 6，2026-07-20）

### cs-b024

**题目**："What is 'cache affinity' in multiprocessor scheduling, and why should a scheduler try to preserve it?"

**检索query**："cache affinity in multiprocessor scheduling and why scheduler should preserve it"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched-multi.pdf/p0005/0010`（cache affinity定义） | 0.2266 | 能，核心论据 |
| `cpu-sched-multi.pdf/p0006/0013`（SQMS的affinity机制） | 0.3197 | 部分能 |
| `cpu-sched-multi.pdf/p0007/0015`（affinity fairness讨论） | 0.3520 | 部分能 |
| `cpu-sched-multi.pdf/p0010/0030`（SQMS/MQMS对比总结） | 0.3536 | 部分能 |
| `cpu-sched-multi.pdf/p0008/0018`（MQMS的cache affinity优势） | 0.3684 | 能 |

**回答是否准确**：准确，正确解释了cache affinity的概念及调度器应保持它的原因。

**具体分析**：5个chunk全部来自本章，检索质量正常。

### cs-b025

**题目**："SQMS（单队列多处理器调度）的两个主要缺点是什么？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched-multi.pdf/p0006/0011`（SQMS扩展性问题：锁竞争） | 0.3170 | 能，核心论据 |
| `cpu-sched-multi.pdf/p0010/0030`（SQMS/MQMS对比总结） | 0.3322 | 部分能 |
| `cpu-sched-multi.pdf/p0007/0015`（SQMS不易保持cache affinity） | 0.3547 | 能，核心论据 |
| `cpu-sched-multi.pdf/p0007/0016`（MQMS介绍，非SQMS缺点） | 0.3715 | 不能 |
| `cpu-sched-multi.pdf/p0008/0018`（MQMS优势） | 0.3860 | 不能 |

**回答是否准确**：准确，扩展性差（锁竞争）+cache affinity差两点都答对。

**具体分析**：两个核心论据chunk分别排第1、第3，检索质量正常。

### cs-b026

**题目**："How does MQMS (Multi-Queue Multiprocessor Scheduling) address the problem of load imbalance across CPUs?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched-multi.pdf/p0007/0016`（MQMS介绍） | 0.2222 | 部分能 |
| `cpu-sched-multi.pdf/p0008/0018`（MQMS引出负载不均衡问题） | 0.2352 | 部分能 |
| `cpu-sched-multi.pdf/p0010/0030`（SQMS/MQMS对比总结） | 0.2512 | 部分能 |
| `cpu-sched-multi.pdf/p0008/0024`（"CPU 0 is idle!"负载不均衡例子+migration方案） | 0.2717 | 能，核心论据 |
| `cpu-sched-multi.pdf/p0006/0011`（SQMS介绍，非MQMS本身） | 0.2825 | 不能 |

**回答是否准确**：准确，正确解释了migration（任务迁移）机制。

**具体分析**：核心论据chunk排第4但仍在top-5内，5个score普遍偏低（0.22~0.28），检索质量良好。

### cs-b027

**题目**："系统有 2 个 CPU，各自维护独立就绪队列。CPU0 有任务 A(10ms)、B(10ms)，CPU1 有任务 C(10ms)、D(10ms)、E(10ms)。不做负载均衡，CPU0 和 CPU1 各自完成所有任务需多少 ms？空闲多少 ms？"

**检索query**（触发2次retrieve）：
1. "多核系统中每个CPU独立处理任务的调度机制"
2. "任务调度中周转时间的定义和计算方法"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched-multi.pdf/p0007/0016`（MQMS介绍） | 0.3537 | 部分能 |
| `java-ch1-e2e.epub/p0006/0069`（多核计算机介绍，跨书无关） | 0.3620 | 不能 |
| `cpu-sched-multi.pdf/p0008/0021`（RR多核调度示例） | 0.3702 | 部分能 |
| `cpu-sched-multi.pdf/p0002/0003`（单核多核缓存差异背景） | 0.3792 | 不能 |
| `cpu-sched-multi.pdf/p0009/0027`（负载均衡后的调度示例） | 0.3890 | 部分能 |
| （另5个chunk来自cpu-sched.pdf，均为通用调度算法内容，不直接支撑本题） | 0.40~0.43 | 不能 |

**回答是否准确：不准确**。回答给出"CPU0总耗时20ms，无空闲；CPU1总耗时30ms，无空闲"，与标准答案（CPU0应空闲10ms）矛盾——模型只计算了每个CPU处理自己队列的总耗时，完全没有考虑"CPU0在20ms完成后，系统整体还要等CPU1跑到30ms"这层含义，即CPU0相对系统整体完成时间有10ms的空闲。

**具体分析**：**这是一次纯粹的推理错误，检索和工具调用都没有问题**——10个citation里虽然没有精确对应"两个独立队列各自耗时+空闲"这个具体场景的chunk，但书里恰恰有一句和这道题的教学意图完全一致的原文"How terrible – CPU 0 is idle!"（出自负载不均衡的示例讲解），检索也确实调用了calculate工具（表明模型知道这是计算题），但模型没有把"CPU0比CPU1提前完成"这层关系转化为"CPU0要等待、因此产生空闲"的结论，属于对题目语义的理解偏差，不是检索或工具调用的问题。

### cs-b056

**题目**："Linux社区实际使用的三种调度器实现——O(1)调度器、完全公平调度器（CFS）、BF调度器（BFS）——分别是单队列还是多队列设计？"

**检索query**："Linux内核中O(1)调度器、完全公平调度器(CFS)和BF调度器(BFS)的实现是单队列还是多队列设计"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-sched-multi.pdf/p0010/0029`（明确写"Both O(1) and CFS use multiple queues, whereas BFS uses a single queue"） | 0.2502 | **能，精确命中原文** |
| `cpu-sched-multi.pdf/p0010/0030`（SQMS/MQMS对比总结） | 0.3966 | 不能 |
| `cpu-sched.pdf/p0002/0006`（FIFO介绍，跨章节无关） | 0.4628 | 不能 |
| `cpu-sched-multi.pdf/p0007/0016`（MQMS介绍） | 0.4726 | 不能 |
| `cpu-sched-multi.pdf/p0008/0021`（RR多核调度示例） | 0.4794 | 不能 |

**回答是否准确**：准确，三种调度器的单/多队列归属全部答对。

**具体分析**：核心论据chunk排名第1且score明显低于其余4个（0.25 vs 0.40+），检索精确命中。

### cs-b057

**题目**："How does the operating system decide which tasks to schedule on the CPU versus offloading to the GPU in a system with heterogeneous processors?"（出题前已核实`GPU`/`heterogeneous`/`graphics`语料库均0命中）

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cpu-api.pdf/p0003/0009`（调度器不确定性） | 0.3378 | 不能 |
| `cpu-sched-multi.pdf/p0005/0010`（cache affinity） | 0.3562 | 不能 |
| `cpu-sched-multi.pdf/p0002/0003`（单核多核缓存差异） | 0.3671 | 不能 |
| `cpu-sched-multi.pdf/p0007/0016`（MQMS介绍） | 0.3673 | 不能 |
| `cpu-sched.pdf/p0010/0031`（STCF子任务拆分） | 0.3700 | 不能 |

**回答是否准确**：准确拒答——"None of the retrieved chunks directly address how an operating system decides whether to schedule tasks on the CPU or offload them to the GPU... I cannot provide an answer based on the book's content."，清楚说明检索内容不支撑这个问题。

**具体分析**：又一个不点名pdf/章节、用自然技术问句的无答案题案例，效果良好——5个score都在0.34~0.37，没有一个能支撑答案，模型没有被表面关键词（如"scheduling"）带偏，正确判断出这是超出语料范围的问题。

---

## threads-intro.pdf 章节（Task 7，2026-07-20）

### cs-b028

**题目**："What is the core difference between a thread and a process in terms of address space?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0002/0002`（多线程地址空间/独立栈） | 0.2897 | 能，核心论据 |
| `threads-intro.pdf/p0001/0000`（线程共享地址空间的定义） | 0.3055 | 能，核心论据 |
| `cpu-sched-multi.pdf/p0002/0003`（硬件缓存差异，跨章节无关） | 0.3835 | 不能 |
| `threads-intro.pdf/p0005/0009`（线程创建类比函数调用） | 0.3926 | 部分能 |
| `threads-intro.pdf/p0002/0003`（使用线程的动机，非本题范围） | 0.3935 | 不能 |

**回答是否准确**：准确，正确解释了线程共享地址空间、进程独立地址空间。

**具体分析**：两个核心论据chunk排名前2，检索质量正常。

### cs-b029

**题目**："使用多线程而非多进程的两个主要动机是什么？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0002/0003`（并行+I/O重叠两大动机） | 0.3822 | 能，核心论据 |
| `java-ch1-e2e.epub/p0006/0070`（Java多线程共享变量问题，跨书无关） | 0.4075 | 不能 |
| `cpu-sched-multi.pdf/p0010/0030`（SQMS/MQMS对比总结，跨章节无关） | 0.4268 | 不能 |
| `cpu-sched-multi.pdf/p0008/0022`（负载不均衡示例，跨章节无关） | 0.4353 | 不能 |
| `java-ch1-e2e.epub/p0006/0069`（多核计算机介绍，跨书无关） | 0.4383 | 不能 |

**回答是否准确**：准确，并行+避免I/O阻塞两点都答对。

**具体分析**：5个citation里只有1个（排第1）真正相关，其余4个（2个跨书Java、2个跨章节cpu-sched-multi）都是噪音，噪音比例80%——回答准确说明核心论据虽然只有1个但排名靠前、内容完整（原文明确列出两大动机），单个高质量chunk仍能支撑住答案。

### cs-b030

**题目**："What is a race condition? Explain using the example of a shared counter variable."

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0011/0028`（竞态条件定义+counter=50例子） | 0.3816 | 能，核心论据 |
| `threads-intro.pdf/p0013/0036`（本章小结，含关键术语ASIDE） | 0.4332 | 部分能 |
| `threads-intro.pdf/p0015/0039`（参考文献列表） | 0.4445 | 不能 |
| `threads-api.pdf/p0008/0040`（信号量代码片段，跨章节无关） | 0.4636 | 不能 |
| `vm-paging.pdf/p0008/0021`（汇编指令示例，跨章节无关） | 0.4797 | 不能 |

**回答是否准确**：准确，且回答里举的例子沿用了书中原文的具体数值（counter初始值50），跟书本身的示例吻合。

**具体分析**：核心论据chunk排名第1，检索质量正常。

### cs-b031

**题目**："临界区（critical section）指的是什么代码？我们希望对临界区实现什么性质，以避免竞态条件？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0013/0036`（关键术语总结） | 0.4117 | 部分能 |
| `threads-intro.pdf/p0011/0028`（临界区+互斥定义） | 0.4418 | 能，核心论据 |
| `vm-segmentation.pdf/p0001/0001`（分段机制，跨章节无关） | 0.5428 | 不能 |
| `cpu-intro.pdf/p0006/0008`（进程状态转换图，跨章节无关） | 0.5446 | 不能 |
| `threads-api.pdf/p0006/0021`（pthread_mutex真实代码，跨章节但话题相关） | 0.5590 | 部分能 |

**回答是否准确**：准确，临界区定义+互斥性质都答对。

**具体分析**：核心论据chunk排名第2，检索质量正常，跨章节的pthread_mutex代码片段虽然不是本章内容，但话题上跟"互斥"呼应，不算严重噪音。

### cs-b032

**题目**："Why might a single line of code like counter++ not be atomic?"

**检索query**："atomic operation and why counter++ is not atomic"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0012/0033`（三条汇编指令原文） | 0.4825 | 能，核心论据 |
| `threads-intro.pdf/p0010/0022`（x86汇编代码序列说明） | 0.4925 | 能，核心论据 |
| `threads-intro.pdf/p0011/0028`（竞态条件定义） | 0.5083 | 部分能 |
| `threads-intro.pdf/p0013/0036`（本章小结） | 0.5232 | 部分能 |
| `java-ch1-e2e.epub/p0005/0038`（Java代码片段，跨书无关） | 0.5336 | 不能 |

**回答是否准确**：准确，三步指令（读-加-写）+切换时机导致覆盖的机制解释正确。

**具体分析**：两个核心论据chunk排名前2，检索质量正常。

### cs-b033

**题目**："在读-改-写三条指令模型（load到寄存器、寄存器加一、写回内存）下，两个线程各对同一个counter变量执行1000次自增、完全不加锁，counter最终值可能的范围是多少？"（题目本身及标准答案`[1000,2000]`都已核实数学上正确，是并发编程"lost update"问题的经典范围公式`[N,2N]`）

**检索query**："读-改-写三条指令模型（load, increment, store）在多线程无锁环境下的竞态条件问题"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0011/0026`（真实追踪表，含counter=50的完整interleaving过程） | 0.4262 | 能，核心论据 |
| `threads-intro.pdf/p0010/0024`（x86汇编三条指令说明） | 0.4276 | 能，核心论据 |
| `threads-api.pdf/p0008/0035`（条件变量等待代码，跨章节但话题相关） | 0.4285 | 不能 |
| `java-ch1-e2e.epub/p0004/0025`（Java流并行概念，跨书无关） | 0.4314 | 不能 |
| `threads-intro.pdf/p0013/0036`（本章小结） | 0.4394 | 部分能 |

**回答是否准确**：准确，且推导过程清晰——正确给出通用公式"两个线程各执行N次自增，最终值范围是`[2N-N, 2N]`即`[N, 2N]`"，代入N=1000得出`[1000, 2000]`，逻辑连贯。

**具体分析**：题目改用书中"读-改-写三条指令"这个具体表述重出后，检索质量明显改善——两个核心论据chunk排名前2，跨书Java EPUB内容从原来占5个citation里4个（80%）降到只剩1个（20%），且不再是最高分。原版泛泛问"counter++"这个通用编程概念，容易跟java-ch1-e2e.epub讨论的"共享可变状态"概念级碰撞；贴近书本身的具体机制描述后，检索精度显著提升，推导过程也不再需要靠拼凑数字硬凑答案。

### cs-b034

**题目**："How exactly do coroutines implement cooperative switching between multiple execution flows within a single thread?"（出题前已核实`coroutine`/`green thread`/`async`/`fiber`语料库均0命中）

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-intro.pdf/p0001/0000`（线程抽象介绍，非协程） | 0.4578 | 不能 |
| `threads-api.pdf/p0007/0032`（pthread_cond_wait/signal，非协程） | 0.4669 | 不能 |
| `threads-intro.pdf/p0007/0011`（线程访问共享数据示例） | 0.4759 | 不能 |
| `threads-intro.pdf/p0013/0036`（本章小结） | 0.4833 | 不能 |
| `cpu-sched-multi.pdf/p0007/0016`（MQMS介绍，跨章节无关） | 0.4857 | 不能 |

**回答是否准确：不准确，幻觉**。5个chunk没有一个提到协程，但模型给出了完整、具体的协程实现细节——yield机制、状态保存、调度器维护ready队列、甚至提到"In languages like Python, coroutines are implemented using generators or async/await constructs"，全部是训练知识编造。

**具体分析**：跟cs-b014、cs-b023同类，都是"检索完全不相关但模型自己对这个常识性CS概念有强训练知识"导致的自信编造。这道题的话题选择本身没问题（避开了元提问模板，也确认了语料库里真实0命中），说明"换成自然问法"能避开"关键词表面碰撞"这类陷阱（详见"遇到的问题"第10条），但避不开"模型自己就懂这个概念、不需要书本依据也能编出一套像模像样的解释"这类幻觉——这是issue #40要处理的核心场景，不是题目设计能解决的。
---

## threads-api.pdf 章节（Task 8，2026-07-20）

### cs-b035

**题目**："What are the four parameters of pthread_create()?"

**检索query**："four parameters of pthread_create()"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-api.pdf/p0002/0004`（int参数的备选声明形式，非本题四参数） | 0.3648 | 不能 |
| `threads-api.pdf/p0002/0009`（pthread_join声明，非本题） | 0.3679 | 不能 |
| `threads-api.pdf/p0001/0002`（pthread_create原始声明） | 0.3721 | 能，核心论据 |
| `threads-api.pdf/p0002/0006`（void指针参数的备选声明形式，非本题） | 0.3786 | 不能 |
| `threads-api.pdf/p0001/0003`（逐个解释thread/attr/start_routine/arg四个参数含义） | 0.4172 | 能，最直接支撑 |

**回答是否准确**：准确，四个参数的类型和含义全部答对。

**具体分析**：最直接支撑答案的chunk（`p0001/0003`）排名第5、score反而最高，两个真正相关的chunk一头一尾，中间3个都是同一函数不同参数组合的备选声明示例（`pthread_create`重载写法），score跟真正相关内容差距很小（0.365~0.379 vs 0.372/0.417），排序区分度不高，但答案本身没受影响。

### cs-b036

**题目**："pthread_join() 的作用是什么？是否所有多线程程序都必须调用它？"

**检索query**："pthread_join() 的作用以及在多线程程序中是否必须调用"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-api.pdf/p0002/0009`（pthread_join函数声明） | 0.2721 | 部分能 |
| `threads-api.pdf/p0005/0017`（完整说明：阻塞等待+web server可不join的例子） | 0.2934 | 能，最直接支撑 |
| `threads-api.pdf/p0003/0011`（join两个参数的具体含义） | 0.3532 | 部分能 |
| `threads-api.pdf/p0007/0032`（pthread_cond_wait/signal声明，非本题） | 0.3548 | 不能 |
| `threads-intro.pdf/p0002/0003`（为什么用线程的一般性动机，跨章节无关） | 0.3690 | 不能 |

**回答是否准确**：准确，阻塞等待+取返回值的作用讲对，"web server这类长期运行程序可以不join、任务型程序通常需要join"的举例跟书中原文（`p0005/0017`）几乎一一对应。

**具体分析**：最直接支撑答案的chunk排名第2且score最低，检索质量良好，5个chunk里3个真实相关。

### cs-b037

**题目**："When waiting on a condition variable, why does the book recommend rechecking the condition in a while loop instead of using a one-time if check?"

**检索query**："why use while loop for condition variable wait instead of if statement"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-api.pdf/p0008/0037`（原文："re-checks the condition in a while loop, instead of a simple if statement...using a while loop is the simple and safe thing to do"） | 0.3633 | 能，核心论据 |
| `threads-api.pdf/p0007/0033`（cond_wait基本定义） | 0.3887 | 部分能 |
| `threads-api.pdf/p0008/0035`（等待代码示例） | 0.4054 | 部分能 |
| `threads-api.pdf/p0008/0038`（改写成spin-wait的对比写法） | 0.4169 | 不能 |
| `threads-api.pdf/p0007/0031`（条件变量总体介绍） | 0.4206 | 不能 |

**回答是否准确**：基本准确，"while循环重新检查、避免虚假唤醒（spurious wakeup）导致误判"这个结论正确，但检索到的核心chunk（`p0008/0037`）原文只说"我们后面章节再详细讨论这个问题，但用while循环是安全的做法"，并没有出现"spurious wakeup"这个术语或具体机制解释——这部分是模型自己补充的标准术语和原理，不是本次ingest语料明确写出的内容。

**具体分析**：核心chunk排名第1，检索质量正常。回答准确但存在部分内容（spurious wakeup机制）依赖模型自身知识而非检索文本这一情况，跟"遇到的问题"第7条类似的浅层部分依赖模式，但这里不算幻觉——因为这确实是while写法在通用pthread语境下公认的正确原因，跟检索到的"用while是安全做法"结论方向一致，不矛盾。

### cs-b038

**题目**："POSIX 线程库提供了哪两种初始化互斥锁（mutex）的方式？"

**检索query**："POSIX线程库中互斥锁（mutex）的两种初始化方式"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-api.pdf/p0006/0023`（静态初始化PTHREAD_MUTEX_INITIALIZER） | 0.3612 | 能，核心论据 |
| `threads-api.pdf/p0007/0034`（静态初始化的典型用法示例） | 0.3936 | 部分能 |
| `threads-api.pdf/p0005/0019`（lock/unlock函数声明，非初始化） | 0.4072 | 不能 |
| `threads-api.pdf/p0006/0025`（动态初始化pthread_mutex_init） | 0.4093 | 能，核心论据 |
| `threads-api.pdf/p0006/0022`（引出"POSIX提供两种初始化锁的方式"这句原文） | 0.4192 | 能，引出论点 |

**回答是否准确**：准确，静态（`PTHREAD_MUTEX_INITIALIZER`）+ 动态（`pthread_mutex_init()`）两种方式都答对，示例代码跟原文一致。

**具体分析**：5个chunk里4个真实相关，检索质量良好。

### cs-b039

**题目**："以下加锁代码有两处问题，分别是什么？`pthread_mutex_t lock; pthread_mutex_lock(&lock); x = x + 1; pthread_mutex_unlock(&lock);`"

**检索query**："C语言中 pthread_mutex_lock 的正确使用方式和常见错误"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `threads-api.pdf/p0007/0034`（正确初始化的典型用法示例） | 0.2347 | 部分能 |
| `threads-api.pdf/p0006/0023`（静态初始化写法） | 0.2552 | 能，支撑问题1 |
| `threads-api.pdf/p0005/0019`（lock/unlock函数声明） | 0.2756 | 不能 |
| `threads-api.pdf/p0006/0021`（题目代码本身的原文出处，逐字一致） | 0.2792 | 能，核心论据 |
| `threads-api.pdf/p0006/0025`（动态初始化+`assert(rc==0)`检查返回值） | 0.2835 | 能，支撑问题2 |

**回答是否准确**：准确，正确指出①未初始化锁、②未检查lock/unlock调用是否成功两处问题，跟标准答案一致。

**具体分析**：题目代码逐字取自`p0006/0021`原文（score最低、排名第4但内容精确匹配），5个chunk全部来自本章且都跟两处bug直接或间接相关，检索质量良好，回答里补充给出的"修正后代码"额外加了错误处理，属于合理延伸，不影响准确性判断。

### cs-b040

**题目**："If multiple threads mostly just read shared data and rarely write to it, how exactly does pthread's read-write lock (rwlock) let multiple readers hold the lock at the same time and only enforce exclusion when a writer needs it?"（出题前已核实`rwlock`/`read-write lock`/`reader-writer`在整个语料库里均0命中）

**检索query**（触发3次retrieve，语义高度重复，均在"rwlock允许多读者/写者互斥"这一个意思上换措辞）：
1. "pthread read-write lock mechanism for allowing multiple readers while enforcing exclusive access for writers"
2. "how pthread read-write lock (rwlock) allows multiple readers concurrently while ensuring exclusive access for writers"
3. "implementation details of pthread read-write lock (rwlock) for concurrent reading and exclusive writing"

15个citation（含大量重复，实际去重后6个不同chunk：`p0007/0028`、`p0006/0023`、`p0007/0034`、`p0005/0019`、`p0009/0045`、`p0006/0021`），score集中在0.35~0.47，全部是mutex/condition variable相关内容，没有一个涉及rwlock。

**回答是否准确：文字表述诚实，但引用标记具有误导性**。模型正文明确写道："The retrieved results still do not contain information about the implementation details of pthread_rwlock_t... Since I cannot find specific information in the provided documents, I will explain the general concept... based on standard knowledge"——清楚承认检索无关、后续内容纯靠通用知识。但由于`citations`列表非空（retrieve确实返回了内容，即便不相关），回答末尾仍被机械挂上`[引用来源：...]`标签，跟正文的诚实免责声明相矛盾。

**具体分析**：这是本轮审查见到的模型在文字表达上最诚实的一次无答案题应对——3次换角度检索确认真的找不到后，没有像cs-b014、cs-b023、cs-b034那样自信编造，而是清楚区分"检索到的内容"和"我基于通用知识的补充"。真正的问题出在引用标签机制上，见"遇到的问题"第13条。

---

## vm-paging.pdf 章节（Task 9，2026-07-20）

### cs-b041

**题目**："In paging, what is the difference between a page and a page frame?"

**检索query**："difference between a page and a page frame in paging"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0006/0016`（线性页表+valid bit，非本题重点） | 0.3964 | 部分能 |
| `vm-paging.pdf/p0003/0005`（page table记录虚拟页到物理帧的映射） | 0.4146 | 部分能 |
| `vm-paging.pdf/p0012/0039`（分页优势总结） | 0.4232 | 不能 |
| `vm-paging.pdf/p0002/0003`（page frame固定大小槽位介绍） | 0.4288 | 能，核心论据 |
| `vm-paging.pdf/p0005/0012`（Figure 18.4页表映射图示） | 0.4349 | 能，核心论据 |

**回答是否准确**：准确，page是虚拟地址空间的逻辑单位、page frame是物理内存的实际单位这一区别讲对，还引用了原文Figure 18.2的具体映射例子。

**具体分析**：5个chunk全部来自本章，虽然score普遍不低（0.40~0.43，排序区分度一般），但都跟分页机制相关，无跨书/跨章节污染。

### cs-b042

**题目**："一个虚拟地址在分页系统中如何被划分为 VPN 和 offset？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0004/0011`（Figure 18.3地址转换流程图示） | 0.2594 | 部分能 |
| `vm-paging.pdf/p0004/0009`（21=010101的具体划分示例） | 0.2737 | 能，核心论据 |
| `vm-paging.pdf/p0003/0007`（VPN/offset位划分表格） | 0.2770 | 能，核心论据 |
| `vm-paging.pdf/p0004/0008`（2位VPN+4位offset的推导） | 0.2902 | 能，核心论据 |
| `vm-paging.pdf/p0008/0024`（VPN_MASK/SHIFT实现细节） | 0.3088 | 部分能 |

**回答是否准确**：准确，高位VPN+低位offset的划分原则讲对，还用书中同一个例子（21=010101，页大小16字节）复现了完整推导过程。

**具体分析**：5个chunk全部真实相关，检索质量良好。

### cs-b043

**题目**："What is the role of the valid bit in a page table entry (PTE)?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0006/0016`（valid bit定义+trap行为） | 0.3179 | 能，核心论据 |
| `vm-paging.pdf/p0007/0017`（x86 PTE位结构图示，非valid bit本身） | 0.3422 | 部分能 |
| `vm-paging.pdf/p0007/0019`（x86中valid/present bit合并的细节） | 0.3594 | 能 |
| `vm-paging.pdf/p0007/0018`（protection/present/dirty/reference等其他位，非valid bit） | 0.3816 | 不能 |
| `vm-paging.pdf/p0005/0014`（页表体积讨论，非valid bit） | 0.4678 | 不能 |

**回答是否准确**：准确，valid bit的作用（标记转换是否有效、触发trap、支持稀疏地址空间节省内存）全部答对，还补充了x86里valid/present bit合并的细节，跟检索到的chunk一致。

**具体分析**：核心chunk排名第1，检索质量良好。

### cs-b044

**题目**："为什么书中说最朴素的分页机制会让内存访问变慢？"

**检索query**："最朴素的分页机制如何导致内存访问变慢"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0005/0014`（32位系统页表体积推导） | 0.4036 | 部分能 |
| `vm-paging.pdf/p0012/0039`（分页优缺点总结） | 0.4121 | 部分能 |
| `vm-paging.pdf/p0008/0020`（引出"页表也会拖慢速度"） | 0.4189 | 能 |
| `vm-paging.pdf/p0009/0028`（原文明确写"factor of two or more"） | 0.4254 | 能，最直接支撑 |
| `vm-paging.pdf/p0006/0016`（线性页表组织方式，非速度问题） | 0.4315 | 不能 |

**回答是否准确**：准确，正确指出每次访存需要先查一次页表再访问真正目标地址，逐字引用了原文"Extra memory references are costly, and in this case will likely slow down the process by a factor of two or more"。

**具体分析**：最直接支撑答案的chunk排名第4，但内容本身足够清楚，回答未受排序影响。

### cs-b045

**题目**："According to the book's summary, what fragmentation-related advantage does paging have over previous approaches like segmentation, and why?"

**检索query**："paging vs segmentation in terms of fragmentation advantages"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0012/0039`（分页优势总结，明确写不产生external fragmentation） | 0.3055 | 能，核心论据 |
| `vm-segmentation.pdf/p0010/0028`（分段产生外部碎片的具体原因） | 0.3624 | 能，对比论据 |
| `vm-paging.pdf/p0001/0000`（分页/分段两种思路的引入） | 0.4212 | 部分能 |
| `vm-paging.pdf/p0002/0003`（固定大小槽位介绍） | 0.4308 | 部分能 |
| `vm-segmentation.pdf/p0001/0001`（分段机制定义） | 0.4398 | 部分能 |

**回答是否准确**：准确，"分页不产生外部碎片、因为固定大小单元不存在大小不匹配问题"这个核心论点讲对，跨章节引用`vm-segmentation.pdf`解释分段为什么会产生外部碎片是合理的对比论据，不算污染。

**具体分析**：核心chunk排名第1，跨书chunk服务于对比论证，检索质量良好。

### cs-b046

**题目**："系统使用 32 位虚拟地址，页大小 4KB（2^12 字节），按书中地址划分方法，VPN 占多少位？页表最多需要多少个条目？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0004/0008`（书中64字节小例子的划分方法，非本题数值） | 0.2814 | 部分能，仅示范方法 |
| `vm-paging.pdf/p0010/0036`（数组VPN范围例子，非本题） | 0.2927 | 不能 |
| `vm-paging.pdf/p0005/0014`（32位系统4KB页示例：20位VPN、2^20条目，跟题目数值完全一致） | 0.3037 | 能，核心论据 |
| `vm-paging.pdf/p0003/0007`（VPN/offset划分表格） | 0.3401 | 部分能 |
| `vm-paging.pdf/p0001/0001`（书中小例子的引入） | 0.3474 | 不能 |

**回答是否准确**：准确，VPN=20位、页表最多2^20个条目，跟标准答案完全一致，推导过程清晰。

**具体分析**：核心chunk（`p0005/0014`）里的数值（32位地址、4KB页、20位VPN、2^20条目）跟题目设问逐字对应，检索质量良好。这道题是简单的减法+乘方运算，**没有调用calculate工具**，回答自己直接算出32-12=20、2^20=1,048,576，属于个位数量级以外但仍然是模型可靠心算范围内的运算，不算问题（呼应"遇到的问题"第8条已确立的判断标准）。

### cs-b047

**题目**："Following the same style as the book's example: with a 64-byte virtual address space and 16-byte pages, what are the VPN and offset for virtual address 21 (binary 010101)? If that VPN maps to page frame PFN=5, what is the physical address?"

**检索query**："virtual address space with 64-byte size and 16-byte pages: how to calculate VPN and offset from a virtual address"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0004/0008`（2位VPN+4位offset推导） | 0.2020 | 能，核心论据 |
| `vm-paging.pdf/p0003/0007`（VPN/offset划分表格） | 0.2041 | 部分能 |
| `vm-paging.pdf/p0003/0006`（64字节地址空间需6位总长的推导） | 0.2579 | 能，核心论据 |
| `vm-paging.pdf/p0004/0009`（21=010101的具体划分示例，逐字对应题目数值） | 0.2644 | 能，最直接支撑 |
| `vm-paging.pdf/p0008/0024`（VPN_MASK/SHIFT实现细节，同样用21举例） | 0.2726 | 能 |

**回答是否准确：不稳定，会出现完全没有答案的情况**。检索到的5个chunk全部真实相关、其中一个逐字包含题目用到的具体数值（虚拟地址21、二进制010101），检索链路没有问题。但同一道题独立测试4次，**全部触发`MAX_ROUNDS_EXCEEDED`**（管线5轮工具调用耗尽，没有产出任何文字回答）。用带工具调用日志的诊断脚本复现后确认根因：模型选择用二进制字符串解析的方式做计算——依次尝试`0b010101 >> 4`（位移）、`int('010101', 2) // 16`（函数调用）等表达式，但`calculate`工具的表达式沙箱只允许四则运算符（`+ - * / // % **`），不允许位移和函数调用，每次都返回明确的中文错误（"不允许的操作: RShift"/"不允许的操作: Call"）。模型收到这个明确反馈后没有调整策略，反复用不同写法重试同一种被禁止的思路，而不是退回十进制算术（`21 // 16`、`21 % 16`，这是允许的运算），最终5轮全部耗尽在这个死循环上。**把题目原样改回中文表述后，3次独立测试全部正常给出正确答案（85）**，检索到的chunk跟英文版一致。这不是提示词没写清楚"允许什么"——`calculate`工具的description已经明确写了"只能包含数字和四则运算符...不允许函数调用或变量"，问题在于模型没有利用工具返回的明确错误信息调整方法，是模型自身工具纠错能力的问题，跟语言措辞的具体关联机制未深入验证。

**具体分析**：这是本轮审查里最严重的"完全无答案"案例——不同于cs-b013/cs-b022那种"答案不稳定但最终有结果"，这道题触发的是管线彻底无输出。跟"遇到的问题"第8条（计算题执行质量问题）同属工具调用/生成稳定性范畴，与issue #40（检索相关性）无关，但因其复现率高（英文4/4失败、中文3/3+首次共4/4成功）、根因明确（工具沙箱语法限制+模型未利用错误反馈调整策略），是本轮记录里最值得后续单独跟进的稳定性问题，详见"遇到的问题"新增条目。

### cs-b048（原无答案题，因ground truth本身矛盾已改判为事实题）

**题目**："为什么页表不直接存放在 MMU 芯片上的专用硬件里，而是存放在内存中？书中提到的最简单的页表组织形式是怎样工作的？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-paging.pdf/p0006/0015`（原文："we don't keep any special on-chip hardware in the MMU...we store the page table for each process in memory"） | 0.3047 | 能，核心论据 |
| `vm-segmentation.pdf/p0003/0005`（分段MMU硬件结构，跨章节非本题） | 0.4221 | 不能 |
| `vm-paging.pdf/p0006/0016`（线性页表定义：数组+VPN索引+PTE查PFN） | 0.4242 | 能，核心论据 |
| `vm-paging.pdf/p0002/0003`（page frame固定槽位介绍） | 0.4439 | 不能 |
| `vm-paging.pdf/p0003/0005`（free list管理空闲页帧，非本题） | 0.4441 | 不能 |

**回答是否准确**：准确，页表太大以至于MMU没有片上专用硬件、因此存放在内存中的原因讲对，线性页表（数组+VPN索引+查PTE取PFN）的工作方式也讲对。

**具体分析**：这道题原为无答案题（"vm-paging这章详细介绍了多级页表的具体实现吗"），但`ground_truth_bookagent.json`里这道题早已标注了真实chunk_id（`p0006/0015`、`p0006/0016`），跟"无答案题"分类自相矛盾——这两个chunk真实存在且内容具体，只是回答的不是"多级页表实现细节"（书中确实没有），而是"页表为什么存内存里、最简单的组织形式是什么"这个相邻但不同的问题。按无答案题的判定标准，若某个话题下能找到chunk支撑，就说明当初题目或分类出错，此处属于分类错误：已把题目改写成这两个chunk真正能回答的问题，`question_type`相应改为事实题。

### cs-b058（新增无答案题）

**题目**："To avoid paying the extra memory access needed to walk the page table on every single memory reference, does the hardware use a small on-chip cache that holds recently used virtual-to-physical translations, and if so, how does it decide when a cached translation can still be reused versus when it needs to be re-fetched from the page table?"（出题前已核实：`TLB`/`Translation Lookaside Buffer`在vm-paging.pdf全文0命中；`TLB`在cpu-sched.pdf、cpu-sched-multi.pdf里各出现1次，均只是作为"on-chip硬件状态"的例子一笔带过，未展开解释工作原理）

**检索query**（触发3次retrieve）：
1. "hardware mechanism for caching virtual-to-physical address translations to avoid frequent page table walks"
2. "hardware TLB (Translation Lookaside Buffer) and its role in caching virtual-to-physical translations"
3. "how TLB decides when to cache a translation and when to invalidate it"

15个citation，去重后11个不同chunk，score集中在0.31~0.56，全部是页表基础机制/分段/调度相关内容，没有一个解释TLB的具体工作原理。

**回答是否准确：不准确，严重幻觉**。模型直接给出"Yes, the hardware does use a small on-chip cache...This cache is known as the Translation Lookaside Buffer (TLB)"，随后详细描述了validity bit机制、LRU替换策略、页表更新时的TLB失效处理——全部是训练知识编造，且没有任何一句免责声明，比cs-b014、cs-b023更彻底：连"检索内容不支撑"这个观察都没提，直接给出确定性答案。

**具体分析**：这是本轮审查里语气最自信、最没有保留的一次幻觉——3次换角度检索都没找到TLB工作原理相关内容，模型仍然把训练知识里对TLB的标准理解（LRU替换、validity bit、失效更新）当作从检索内容里得出的结论呈现，完全没有触发"未查找到相关资料"这条system prompt指令。跟cs-b040（同样检索不到、但诚实声明）形成鲜明对比，说明这条指令能不能被触发，很大程度上取决于具体问题和模型当时的"自信程度"，不稳定。

---

## vm-segmentation.pdf 章节（Task 10，2026-07-20）

### cs-b049

**题目**："How does the segmentation mechanism perform address translation? Under what circumstances does it trigger a segmentation fault?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0012/0031`（segmentation.py练习题介绍，非本题） | 0.3332 | 不能 |
| `vm-segmentation.pdf/p0004/0009`（段寄存器/显式分段方式） | 0.3958 | 能，核心论据 |
| `vm-segmentation.pdf/p0008/0025`（分段整体回顾，非地址转换细节） | 0.4065 | 部分能 |
| `vm-segmentation.pdf/p0012/0032`（练习题具体内容，非本题） | 0.4093 | 不能 |
| `vm-segmentation.pdf/p0010/0028`（分段解决的问题总览） | 0.4232 | 部分能 |

**回答是否准确**：准确，base+bounds地址转换机制、越界触发段错误的原因都答对。

**具体分析**：核心chunk`p0004/0009`只排第2，5个chunk里2个是练习题相关内容（不支撑本题），排序质量一般但答案未受影响。

### cs-b050

**题目**："分段机制会产生什么类型的碎片？书中是如何描述这一问题的？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0009/0026`（外部碎片定义，含20KB/24KB具体例子） | 0.4860 | 能，核心论据 |
| `java-ch1-e2e.epub/p0003/0005`（Java多核/并发介绍，跨书无关） | 0.4987 | 不能 |
| `vm-segmentation.pdf/p0007/0022`（粗粒度/细粒度分段，非碎片） | 0.5055 | 不能 |
| `vm-segmentation.pdf/p0008/0025`（分段整体回顾） | 0.5074 | 不能 |
| `vm-paging.pdf/p0001/0000`（分页/分段两种思路对比，跨章节相关） | 0.5188 | 部分能 |

**回答是否准确**：准确，外部碎片定义+具体数值例子+compaction应对方案全部答对，逐字引用了原文"We call this problem external fragmentation"。

**具体分析**：核心chunk排名第1，但跨书Java EPUB内容混入citation第2名，是"遇到的问题"第3条模式的又一实例。

### cs-b051

**题目**："Which segments does a segmented system typically divide a process's address space into?"

**检索query**："segmented system divides process's address space into which segments"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0002/0003`（原文明确写"three logically-different segments: code, stack, and heap"） | 0.3268 | 能，核心论据 |
| `vm-segmentation.pdf/p0008/0025`（分段整体回顾） | 0.3294 | 部分能 |
| `vm-segmentation.pdf/p0012/0031`（练习题介绍，非本题） | 0.3430 | 不能 |
| `vm-segmentation.pdf/p0007/0022`（粗粒度/细粒度分段，提及code/stack/heap） | 0.3452 | 能 |
| `vm-segmentation.pdf/p0003/0005`（MMU硬件结构，三对base/bounds寄存器） | 0.3479 | 部分能 |

**回答是否准确**：准确，"code、stack、heap"三段全部答对，跟核心chunk原文逐字一致。

**具体分析**：核心chunk排名第1，检索质量良好。这道题用中文原文（"分段系统通常将进程地址空间划分为哪几个段？"）单独测试时出现过真实错误——核心chunk同样排名第1、原文同样明确写着"code, stack, and heap"，但回答给出的是"代码段、**静态数据段**、堆栈段"，用"静态数据段"替换了"堆段"，且引用列表里混入了一个跨章节`cpu-intro.pdf`的图示（画的是"code/static data/heap/stack"四个区域）。英文版复测未复现这个错误。这是检索正确、生成环节本身出错的案例，跟cs-b047属于同一类"跨语言生成不稳定"现象，但这次是"中文错、英文对"，方向和cs-b047相反，说明这种不稳定性没有固定的语言偏向，记入"遇到的问题"新增条目。

### cs-b052

**题目**："分段相比之前整个地址空间用一对 base+bounds 映射的方式，解决了什么问题？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0001/0001`（分段概念引入） | 0.3762 | 部分能 |
| `vm-segmentation.pdf/p0006/0016`（栈反向增长，非本题） | 0.4016 | 不能 |
| `vm-segmentation.pdf/p0006/0018`（栈地址转换示例，非本题） | 0.4051 | 不能 |
| `vm-segmentation.pdf/p0005/0014`（分段地址转换伪代码） | 0.4116 | 部分能 |
| `vm-segmentation.pdf/p0002/0003`（避免堆栈间未用空间占用物理内存，核心论据） | 0.4148 | 能，核心论据 |

**回答是否准确**：准确，"避免堆和栈之间未用空间浪费物理内存"这一核心论点讲对，还补充了栈反向增长这类合理延伸。

**具体分析**：核心chunk排名第5但内容仍被正确使用，5个chunk全部来自本章，无跨书/跨章节污染。

### cs-b053

**题目**："Using the same code segment configuration as the book's Figure 16.3 (base=32KB, bounds/size=2KB), is an access at virtual offset=100B legal? What is the physical address?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0006/0018`（栈反向增长转换示例，非本题） | 0.3052 | 不能 |
| `vm-segmentation.pdf/p0003/0007`（原文逐字例子："100 + 32KB, or 32868"） | 0.3152 | 能，最直接支撑 |
| `vm-segmentation.pdf/p0006/0016`（栈反向增长，非本题） | 0.3186 | 不能 |
| `vm-paging.pdf/p0001/0001`（跨章节分页示例，非本题） | 0.3315 | 不能 |
| `vm-paging.pdf/p0004/0008`（跨章节VPN示例，非本题） | 0.3327 | 不能 |

**回答是否准确**：准确，合法+物理地址32868，跟标准答案完全一致，正确调用了calculate工具。

**具体分析**：最直接支撑答案的chunk（题目数值的原始出处）排名第2，其余4个都不相关（含2个跨章节vm-paging.pdf内容），噪音比例80%，但核心chunk内容本身足够精确，答案未受影响。

### cs-b054

**题目**："vm-segmentation 这章讨论了现代 x86-64 处理器中分段寄存器的实际使用方式吗？"

**检索query**："modern x86-64 processors segment registers usage"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0003/0005`（MMU硬件结构，三对base/bounds寄存器） | 0.4010 | 不能 |
| `vm-segmentation.pdf/p0007/0019`（代码段共享/保护位机制） | 0.4150 | 不能 |
| `vm-segmentation.pdf/p0008/0024`（细粒度分段历史，Burroughs B5000等早期机器） | 0.4180 | 不能 |
| `vm-segmentation.pdf/p0005/0015`（隐式分段方法，SEG_MASK等寄存器常量） | 0.4296 | 不能 |
| `vm-segmentation.pdf/p0003/0007`（Figure 16.3代码段配置示例） | 0.4331 | 不能 |

**回答是否准确：结论错误，但对关键事实有明确披露**。回答开头写"是的，vm-segmentation 这一章确实讨论了现代 x86-64 处理器中分段寄存器的实际使用方式"，结尾重申"可以确认...还涉及了现代 x86-64 处理器中如何实际利用这些寄存器"，但在中间的括号说明里明确承认"书中没有直接提到'x86-64'这个具体架构名称"。5个chunk全部是经典分段概念/历史内容，没有一个提到x86-64或任何现代具体架构。

**具体分析**：这道题延用了"这章讨论了X吗"元提问模板（design spec评审阶段已决定保留这一道，用于持续观察这类模板的实际表现）。模型的结论方向错了（该说"没有"却说"是的"），但没有像cs-b014/cs-b023/cs-b034/cs-b058那样对检索内容与自身结论之间的落差完全没有察觉——它明确点出了"x86-64"这个具体术语在原文中不存在，只是没有把这个已经观察到的事实用来修正开头和结尾的结论方向。按"模型是否表现得像书里全说清楚了、自己毫不知情在编"这个标准衡量，这道题不属于最严重的一类，但结论本身确实是错的，如实记录。

### cs-b055（原判无答案题，ground truth订正）

**题目**："vm-segmentation 这章给出了不同外部碎片消减算法（如最佳适应、最差适应）的量化性能对比实验数据吗？"

**检索query**："vm-segmentation chapter, external fragmentation reduction algorithms, quantitative performance comparison experiments"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `vm-segmentation.pdf/p0011/0030`（参考文献列表，含Wilson survey引用） | 0.3922 | 部分能 |
| `vm-segmentation.pdf/p0010/0028`（分段问题总览，提到smart algorithms） | 0.4324 | 部分能 |
| `vm-segmentation.pdf/p0010/0027`（best-fit/worst-fit/first-fit/buddy算法点名，但只有名字没有量化对比） | 0.4519 | 能，核心论据 |
| `vm-segmentation.pdf/p0009/0026`（外部碎片定义，非量化对比） | 0.4524 | 不能 |
| `vm-segmentation.pdf/p0007/0019`（代码段共享，非本题） | 0.4557 | 不能 |

**回答是否准确**：准确，正确指出书中只点了best-fit/worst-fit/first-fit/buddy algorithm这些算法的名字、引用了外部Wilson survey作延伸阅读，但没有给出量化对比数据。

**具体分析**：这道题原本ground truth标注了真实chunk_id（跟cs-b050完全相同的`p0009/0026`+`p0009/0027`），与"无答案题"分类自相矛盾。追查`eval/derive_ground_truth.py`（首次生成ground truth的自动化脚本）发现根因：脚本按正则`\bp(\d+)`匹配`source_location`文本里任何"p数字"模式并直接判定为`page_exact`，完全不检查`question_type`——cs-b055的`source_location`写的是"vm-segmentation.pdf p9（提到存在很多算法...但未给出具体算法的量化对比数据）"，本意是说明"p9附近有相关但不够的内容"，脚本却把这个"p9"当成了真实定位依据，误判为有答案。核实过当前qa.jsonl里全部无答案题，只有cs-b048（已在Task 9修复）和cs-b055受这个bug影响，其余无答案题的`source_location`本来就没有具体页码，没有触发这个问题。cs-b055题目本身不改，ground truth订正为`no_location_expected`。

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

当前system prompt已加入"retrieve返回内容没回答问题时要说明未查找到相关资料"这条指令，但cs-b014证明这条指令对模型自身有强训练知识、根本不觉得"自己不知道"的专业内容（semaphore）完全不起作用——两次retrieve都查不到相关内容，模型依然自信编造一整套教程，没有触发这条指令。这说明检索排序类问题（citation噪音、排名不理想）和"自信编造"类幻觉是两类不同性质的问题：前者能通过改进检索环节本身缓解，后者的根源是模型没有意识到自己在编，不是缺一句提醒，需要issue #40真正的机制（阈值/reranker/低置信度标记），prompt工程这条路走不通。cs-b058（TLB工作原理）是更极端的例子：3次换角度检索、11个不同chunk全部不相关，模型给出的却是全程没有一句保留、语气完全确定的详细幻觉，连cs-b014那种"检索结果没有直接提到"式的过渡都没有，说明这条指令能否触发，除了"模型是否有强训练知识"之外，还跟具体问题、模型当时的"自信程度"有关，触发与否不稳定。

`_append_tool_tags`（详见第13条）进一步说明这条路为什么走不通：系统本身已经不信任模型自己嘴上说"有没有用到资料"，citation标签只认"retrieve是否真的返回了非空结果"这个硬事实，不解析正文措辞——这个设计本身就承认了"模型自我报告是否有依据"不可靠。而"先判断检索内容能不能回答问题、不能就先说明"这条prompt指令，本质上仍然是在要求模型对同一件事（自己是否真的有依据）做一次准确的自我报告，只是换了个问法。系统已经在标签机制上不信任这种自我报告，却又在生成阶段依赖同一种自我报告来防幻觉，逻辑上是自相矛盾的——不管这条指令写得多细、要求模型先做"能否回答"这一步判断再输出，本质上都是在期待模型对自己的知识边界做出准确判断，而cs-b014/cs-b023/cs-b034/cs-b058反复证明这件事本身就不可靠。真正一致的解法只能来自检索链路自己给出可信的相关性信号（阈值/reranker），而不是继续在prompt层面加更多要求模型自我判断的指令。

### 7. 单跳检索对"只描述场景、不给术语"的问题存在真实结构性局限

cs-b010是代表案例：题目原文全程没有出现"zombie"这个词，只描述了"父进程不调用wait()、子进程先退出"的场景。retrieve的query由模型从题目原文生成，没有"zombie"这个锚点，检索自然找不到僵尸进程定义所在的chunk（内容确实存在于语料库里，用精确术语查得到）。这不是"该检索到的没检索到"这种干净的检索bug，也不是题目设计缺陷，而是"单次query-from-question的检索机制，对不给术语只描述场景的问题"天然覆盖不到——这类问题在真实用户场景里很常见（用户经常不知道教科书术语，只会描述现象），是有代表性的测试场景，应作为issue #40设计时的真实案例保留。

### 8. 计算题的执行质量问题：自我怀疑/纠错循环，以及工具调用不规范

两类独立问题：

**生成过程不稳定**：cs-b013（4次测试2次开头给错答案）、cs-b022（开头给错"50ms"、FIFO算术算错、混淆书中另一算例的数字，反复重算三次才收敛到正确答案）——检索到的chunk本身基本相关，问题完全出在生成/推理环节。

**calculate工具调用不规范，两个方向都有**：cs-b006这类个位数加减法（10-1+1）完全没调用calculate，system prompt里"任何数值计算都必须调用"这条规则对这种量级的算术不合理，不算这道题的问题（已把cs-b006改判事实题）；但cs-b022这边即使调用了calculate、每一步单独计算都对，最后汇总平均值时仍然漏除以3（"(5+15+35)/3=55ms"），说明工具调用本身不能保证最终答案的数值组合正确，容错点在工具调用前后的"整合"这一步。

**calculate工具语法被拒后，模型不会调整策略、彻底耗尽轮数**：cs-b047是比上述两类更严重的情况——不是"答错"而是"完全无输出"。检索质量、工具描述本身都没有问题（`calculate`工具的description已明确写"只能包含数字和四则运算符...不允许函数调用或变量"），但英文措辞下模型连续4次独立测试都选择用二进制字符串解析（`0b010101 >> 4`、`int('010101', 2) // 16`等）做这道题，每次都拿到工具返回的明确中文错误（"不允许的操作: RShift"/"不允许的操作: Call"），却没有据此调整为十进制算术（这是允许的运算，中文版就是这么算出正确答案的），反复用不同写法重试同一种被禁止的思路，直到5轮工具调用全部耗尽，回答变成`[MAX_ROUNDS_EXCEEDED]`——用户什么都得不到。同一道题改回中文表述后3次测试全部成功。这不是提示词遗漏了什么信息，而是模型在收到工具明确的错误反馈后，没有把这个反馈用于调整下一步策略，是模型自身的工具纠错/恢复能力问题，具体在什么条件下更容易被特定语言措辞触发未深入验证，值得后续单独关注。

这两类现象都跟issue #40（检索相关性）是不同性质的问题，更像是模型在数值推理/工具编排上的稳定性问题，记录供后续参考，不在这轮处理范围。

### 9. 表面关键词相似但概念不同的内容，会诱导模型做出错误的"确认"式幻觉

cs-b023是典型案例：问题问的是多级反馈队列MLFQ具体怎么调整优先级，检索到的排名第1的chunk原文明确写着"multi-level feedback queue...is the topic of the next chapter"——比"内容不相关"更强的信号，相当于书本身声明"这里不讲"。模型仍然给出了一套具体、看起来合理的MLFQ规则细节，完全忽略了这个显式声明。cpu-sched.pdf这批还有一个更早的实例：原cs-b023版本问EDF，检索到的内容里有个完全不同的概念——Linux BFS调度器用的"Earliest Eligible Virtual Deadline First (EEVDF)"，只因为名字里也带"deadline"，模型的回答写出"检索结果中没有直接提到EDF"却依然用EEVDF反向论证"书里确实讨论了deadline调度"。这两个案例都不是cs-b014那种"检索完全不相关、纯粹凭空编"——是有一个弱信号（名字相似，或者更极端地，一个明确的"下一章才讲"声明）被模型忽略或误用，最终仍然给出了确认式的错误回答。这提示issue #40的判定逻辑除了"有没有检索到内容"之外，还需要考虑"检索到的内容是否明确表明这个话题不在当前范围内"这种更细的情况，单纯判断"retrieve返回是否非空"不足以覆盖这类幻觉。

### 10. 无答案题不能用"这本书/这一章讨论了X吗"这种元提问模板，应该用自然的直接技术问句

审查过程中发现，早期无答案题（包括cs-b007、cs-b014、cs-b023最初的版本）大量采用"cpu-xxx这一章讨论了/讲解了X吗"这种句式——直接向模型提出关于"书本身覆盖范围"的元问题。这类模板本身就是问题的一部分，不只是话题选得好不好的问题：它明着点出pdf/章节名称当问题主语，容易让模型把注意力放在"要不要承认没讲"这种元推理上，而不是老老实实检索、发现内容对不上再判断。cs-b007重出后改成不点名pdf/章节、直接问"是怎么实现的"这种自然技术问句（关于容器隔离机制），结果是本轮处理最好的无答案题案例：模型多次换角度检索（4次）确认真的找不到后，清楚说明这是通用知识而非书本依据，正确挂上`[未找到参考资料]`标签。cs-b057（GPU异构调度）延续这个思路同样效果良好。这说明"元提问模板"本身会干扰模型的正常判断路径，无答案题应该像有答案题一样自然提问，让"找不到依据"成为检索之后自然得出的结论，而不是题目本身就在问"有没有"。

### 11. 检索和工具调用都正确，纯粹是模型自己的推理/语义理解错误，不是这轮审查能改的问题

cs-b027是典型案例：题目问两个独立队列的CPU各自完成任务的耗时和空闲时间，检索到的10个chunk里虽然没有精确对应这个具体场景的内容，但书中原文有一句和这道题教学意图完全一致的例句"How terrible – CPU 0 is idle!"（负载不均衡示例的原文），calculate工具也被正确调用。但模型给出的最终答案是"CPU0/CPU1均无空闲"，跟标准答案（CPU0应空闲10ms）矛盾——它只计算了每个CPU自己的任务耗时总和，没有把"CPU0比CPU1提前完成"这层关系转化为"要等待、因此产生空闲"的结论。这是一次纯粹的语义理解/推理错误，检索链路和工具调用链路都没有问题，不在issue #40（检索相关性）范畴内，也不是这轮测试集审查能通过改题目或改prompt解决的问题，如实记录。

### 12. 话题在概念层面跨书重叠时，贴近书本具体表述能显著降低跨书污染

cs-b029（threads-intro.pdf事实题）5个citation里4个（80%）是`java-ch1-e2e.epub`内容，是本轮观察到的高噪音案例——原因是"多线程"这个话题本身在OS书和Java书里都有概念级讨论（OS讲并行/I/O重叠动机，Java讲流并行/共享可变状态），泛化的问法容易两边都命中。cs-b033原本问"counter++"这种通用编程概念时也遇到同样问题（80%噪音，最终数值答案`[1000,2000]`碰巧正确但推导过程明显不连贯，出现"1000+1000-1000=1000"这类凑数表述）；改用书中"读-改-写三条指令"这个具体表述重出后，噪音降到20%，两个核心chunk排到前2名，推导过程也变得连贯清晰（正确给出通用公式`[N,2N]`再代入数值）。这证明**贴近书本身具体术语/机制描述、避免泛化到通用CS概念层面**，能有效缓解这类"话题本身跨书重叠"导致的污染——跟"遇到的问题"第1条（优先用原文术语）是同一个机制在起作用，cs-b033是一个具体、可复现的修复案例。

### 13. 引用标签是否挂出，只看retrieve有没有返回内容，不看模型正文自己怎么说

`pipeline/agent/answer.py`的`_append_tool_tags`逻辑是纯机械化的：`tags = [_citation_tag(citations) if citations else NO_CITATION_TAG]`，只判断这一轮`citations`列表是否非空，完全不解析模型正文里的措辞。cs-b040是这个逻辑产生矛盾结果的实例——检索到的5个chunk全部跟问题（rwlock）无关，模型正文明确写出"the retrieved results still do not contain information about...I will explain the general concept...based on standard knowledge"，诚实承认没有依据；但因为`citations`非空（retrieve确实返回了东西，只是不相关），回答末尾仍被挂上`[引用来源：...]`标签，视觉上像是这段话有书本依据。

这大概率是有意为之：不能信模型自己嘴上说"我用了/没用工具"，只认"是否真的调用了retrieve并拿到非空结果"这个硬事实，防的是模型编造工具使用记录本身。但这个机制回答的是"retrieve有没有被调用且非空"，跟"返回的内容是否真的支撑了这个答案"是两个不同的问题——当前实现把二者划了等号。修复这个问题依赖的是retrieve返回内容的相关性判断能力，是issue #40（相关性阈值/rerank）要解决的同一类问题，不需要现在改标签逻辑本身，留到rerank阶段一并处理。

### 14. 跨语言生成不稳定不止一个方向，检索链路一致时答案仍可能因语言而异

cs-b047（第8条已详述）是英文触发`MAX_ROUNDS_EXCEEDED`完全无输出、中文正常的案例。cs-b051是方向相反的例子：同一道事实题，检索到的核心chunk排名、内容完全一致（原文明确写"code, stack, and heap"），中文提问时模型答成"代码段、静态数据段、堆栈段"（把"堆段"错答成"静态数据段"，还混入了一个跨章节`cpu-intro.pdf`的四区域图示），英文提问时正确答出"code, stack, and heap"。两个案例合在一起说明：检索链路给出同样高质量、同样排序的输入时，生成环节仍可能因提问语言不同而产出不同结果——没有固定的"哪种语言更可靠"的偏向，语言本身是一个会影响生成稳定性的独立变量，不是检索质量问题，也不属于issue #40范畴，记录供后续参考。


