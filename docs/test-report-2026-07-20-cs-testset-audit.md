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

### 8. 计算题的执行质量问题：自我怀疑/纠错循环，以及工具调用不规范

两类独立问题：

**生成过程不稳定**：cs-b013（4次测试2次开头给错答案）、cs-b022（开头给错"50ms"、FIFO算术算错、混淆书中另一算例的数字，反复重算三次才收敛到正确答案）——检索到的chunk本身基本相关，问题完全出在生成/推理环节。

**calculate工具调用不规范，两个方向都有**：cs-b006这类个位数加减法（10-1+1）完全没调用calculate，system prompt里"任何数值计算都必须调用"这条规则对这种量级的算术不合理，不算这道题的问题（已把cs-b006改判事实题）；但cs-b022这边即使调用了calculate、每一步单独计算都对，最后汇总平均值时仍然漏除以3（"(5+15+35)/3=55ms"），说明工具调用本身不能保证最终答案的数值组合正确，容错点在工具调用前后的"整合"这一步。

这两类现象都跟issue #40（检索相关性）是不同性质的问题，更像是模型在数值推理/工具编排上的稳定性问题，记录供后续参考，不在这轮处理范围。

### 9. 表面关键词相似但概念不同的内容，会诱导模型做出错误的"确认"式幻觉

cs-b023是典型案例：问题问的是多级反馈队列MLFQ具体怎么调整优先级，检索到的排名第1的chunk原文明确写着"multi-level feedback queue...is the topic of the next chapter"——比"内容不相关"更强的信号，相当于书本身声明"这里不讲"。模型仍然给出了一套具体、看起来合理的MLFQ规则细节，完全忽略了这个显式声明。cpu-sched.pdf这批还有一个更早的实例：原cs-b023版本问EDF，检索到的内容里有个完全不同的概念——Linux BFS调度器用的"Earliest Eligible Virtual Deadline First (EEVDF)"，只因为名字里也带"deadline"，模型的回答写出"检索结果中没有直接提到EDF"却依然用EEVDF反向论证"书里确实讨论了deadline调度"。这两个案例都不是cs-b014那种"检索完全不相关、纯粹凭空编"——是有一个弱信号（名字相似，或者更极端地，一个明确的"下一章才讲"声明）被模型忽略或误用，最终仍然给出了确认式的错误回答。这提示issue #40的判定逻辑除了"有没有检索到内容"之外，还需要考虑"检索到的内容是否明确表明这个话题不在当前范围内"这种更细的情况，单纯判断"retrieve返回是否非空"不足以覆盖这类幻觉。

### 10. 无答案题不能用"这本书/这一章讨论了X吗"这种元提问模板，应该用自然的直接技术问句

审查过程中发现，早期无答案题（包括cs-b007、cs-b014、cs-b023最初的版本）大量采用"cpu-xxx这一章讨论了/讲解了X吗"这种句式——直接向模型提出关于"书本身覆盖范围"的元问题。这类模板本身就是问题的一部分，不只是话题选得好不好的问题：它明着点出pdf/章节名称当问题主语，容易让模型把注意力放在"要不要承认没讲"这种元推理上，而不是老老实实检索、发现内容对不上再判断。cs-b007重出后改成不点名pdf/章节、直接问"是怎么实现的"这种自然技术问句（关于容器隔离机制），结果是本轮处理最好的无答案题案例：模型多次换角度检索（4次）确认真的找不到后，清楚说明这是通用知识而非书本依据，正确挂上`[未找到参考资料]`标签。这说明"元提问模板"本身会干扰模型的正常判断路径，无答案题应该像有答案题一样自然提问，让"找不到依据"成为检索之后自然得出的结论，而不是题目本身就在问"有没有"。
