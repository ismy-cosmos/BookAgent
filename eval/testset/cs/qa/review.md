# CS 测试集 QA 人工审查版

总计 60 条，按来源章节分组。所有条目均已对照实际 PDF 内容核验，source_location 标注真实页码（早期 cs-b001~b027 部分用书内章节号 §x.x 辅助定位，对照解析结果已核实编号准确）。

## cpu-intro.pdf（7 条，2026-07-20用cs-eval库真实审查过；4条英文/3条中文，中英各类型均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b001 | 事实题 | EN | What is the operating system's precise definition of a "process"? What is the difference between a process and a program? | cpu-intro.pdf §4.1 The Abstraction: A Process |
| cs-b002 | 事实题 | 中 | 进程的机器状态（machine state）由哪三类主要成分构成？ | cpu-intro.pdf §4.1 The Abstraction: A Process |
| cs-b003 | 事实题 | EN | What technique does the operating system use to run multiple processes on a single physical CPU at the same time? What is its core cost? | cpu-intro.pdf 引言及 §4.1 |
| cs-b004 | 事实题 | 中 | OS 将程序加载为进程时，在跳转到 main() 之前会依次完成哪些初始化步骤？ | cpu-intro.pdf §4.3 Process Creation: A Little More Detail |
| cs-b005 | 事实题 | EN | What are the three basic states of a process? What does each mean, and what conditions trigger transitions between them? | cpu-intro.pdf §4.4 Process States |
| cs-b006 | 事实题 | 中 | cpu-intro.pdf 的 Figure 4.4 展示了 Process0 和 Process1 的执行追踪：两者在时间单位1同时到达系统…（数值推导为个位数加减法，够不上计算题分类，改判事实题） | cpu-intro.pdf §4.4 Process States，Figure 4.4 Tracing Process State: CPU and I/O |
| cs-b007 | 无答案题 | EN | How does the operating system give a group of processes their own isolated view of the filesystem and network, the way container runtimes like Docker do? | cpu-intro.pdf（本章及本次ingest全部语料均未涉及容器/namespace隔离机制，container/cgroup/namespace/Docker/chroot在整个语料库里均0命中） |

## cpu-api.pdf（7 条，2026-07-20用cs-eval库真实审查过；3条英文/4条中文，中英各类型均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b008 | 事实题 | EN | What value does fork() return in the parent process versus the child process? What does it return if the call fails? | cpu-api.pdf §5.1 The fork() System Call |
| cs-b009 | 事实题 | 中 | exec() 系列调用成功执行后为什么不会返回到调用它的代码？ | cpu-api.pdf §5.2 The exec() System Call |
| cs-b010 | 事实题 | EN | What does wait() do? What happens if the parent process doesn't call wait() and the child process exits first? | cpu-api.pdf p4 §5.2 The wait() System Call；僵尸状态定义见 cpu-intro.pdf p9 ASIDE: Process List |
| cs-b011 | 事实题 | 中 | fork() 后子进程是否会获得父进程文件描述符的独立副本？这一特性如何支撑 shell 的输出重定向功能？ | cpu-api.pdf p6-p7 §5.4 Why? Motivating The API（重定向示例） |
| cs-b012 | 事实题 | 中 | shell 执行用户输入命令的典型三步流程是什么？ | cpu-api.pdf §5.4 Why? Motivating The API |
| cs-b013 | 计算题 | EN | How many lines of "hello" will the following C code print in total when executed? int main() { fork(); fork(); p… | cpu-api.pdf §5.1 The fork() System Call（fork 调用树分析） |
| cs-b014 | 无答案题 | 中 | 多个用 fork() 创建的兄弟进程之间，操作系统提供了信号量（semaphore）这类同步原语来协调彼此的执行顺序吗？具体是怎么用的？ | cpu-api.pdf（本章及本次ingest全部语料均未涉及semaphore，见test-report真实幻觉案例记录） |

## cpu-sched.pdf（9 条，2026-07-20用cs-eval库真实审查过；4条英文/5条中文，中英各类型均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b015 | 事实题 | EN | In scheduling, what is the formula for calculating "turnaround time"? | cpu-sched.pdf p2 §7.2 Scheduling Metrics |
| cs-b016 | 事实题 | 中 | FIFO 调度在什么情况下会产生「护航效应」（convoy effect）？ | cpu-sched.pdf p3 §7.3 FIFO（Convoy Effect） |
| cs-b017 | 事实题 | EN | Why is SJF (Shortest Job First) difficult to apply directly in real systems? | cpu-sched.pdf p4 §7.4 Shortest Job First (SJF) |
| cs-b018 | 事实题 | 中 | STCF 与 SJF 的主要区别是什么？ | cpu-sched.pdf p5 §7.5 Shortest Time-to-Completion First (STCF) |
| cs-b019 | 事实题 | EN | Why does Round Robin scheduling improve response time but usually result in worse turnaround time? | cpu-sched.pdf p6-p8 §7.6 Response Time / §7.7 Round Robin |
| cs-b020 | 事实题 | 中 | 调度器在处理含 I/O 的任务时，如何实现 CPU 与 I/O 的重叠利用？ | cpu-sched.pdf p9-p10 §7.8 Incorporating I/O |
| cs-b021 | 计算题 | EN | Three tasks A(5ms), B(10ms), and C(15ms) all arrive at t=0. Under FIFO scheduling in the order A→B→C, what is the average turnaround time? | cpu-sched.pdf p3 §7.3 FIFO（计算题，沿用书中方法论） |
| cs-b022 | 计算题 | 中 | 三个任务 A(20ms)、B(5ms)、C(10ms) 同时在 t=0 到达，用 SJF（最短作业优先）调度，平均周转时间是多少？（改为独立题目，不依赖cs-b021上下文） | cpu-sched.pdf p4 §7.4 SJF（计算题，沿用书中方法论） |
| cs-b023 | 无答案题 | 中 | 多级反馈队列调度算法具体是怎么根据进程的历史行为动态调整它所在的队列优先级的？ | cpu-sched.pdf（本章及本次ingest全部语料均未详细讨论多级反馈队列MLFQ的具体调整规则，cpu-sched.pdf p11明确写着MLFQ"is the topic of the next chapter"，cpu-sched-multi.pdf里只有一处一笔带过的类比提及，没有展开讲解队列调整机制本身） |

## cpu-sched-multi.pdf（6 条，2026-07-20用cs-eval库真实审查过，新增cs-b056/cs-b057；3条英文/3条中文，中英各类型均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b024 | 事实题 | EN | What is "cache affinity" in multiprocessor scheduling, and why should a scheduler try to preserve it? | cpu-sched-multi.pdf p5 §10.3 One Final Issue: Cache Affinity |
| cs-b025 | 事实题 | 中 | SQMS（单队列多处理器调度）的两个主要缺点是什么？ | cpu-sched-multi.pdf p6 §10.4 Single-Queue Scheduling |
| cs-b026 | 事实题 | EN | How does MQMS (Multi-Queue Multiprocessor Scheduling) address the problem of load imbalance across CPUs? | cpu-sched-multi.pdf p7-p10 §10.5 Multi-Queue Scheduling（work stealing） |
| cs-b027 | 计算题 | 中 | 系统有 2 个 CPU，各自维护独立就绪队列。CPU0 有任务 A(10ms)、B(10ms)，CPU1 有任… | cpu-sched-multi.pdf p7-p9 §10.5 Multi-Queue Scheduling（负载不均衡示例） |
| cs-b056 | 事实题 | 中 | Linux社区实际使用的三种调度器实现——O(1)调度器、完全公平调度器（CFS）、BF调度器（BFS）——分别是单队列还是多队列设计？ | cpu-sched-multi.pdf p10 §10.6 Linux Multiprocessor Schedulers |
| cs-b057 | 无答案题 | EN | How does the operating system decide which tasks to schedule on the CPU versus offloading to the GPU in a system with heterogeneous processors? | cpu-sched-multi.pdf（本章及本次ingest全部语料均未涉及GPU/异构处理器调度，GPU/heterogeneous/graphics在整个语料库里均0命中） |

## threads-intro.pdf（7 条，2026-07-20用cs-eval库真实审查过；4条英文/3条中文，中英各类型均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b028 | 事实题 | EN | What is the core difference between a thread and a process in terms of address space? | threads-intro.pdf p1-p2 线程模型 |
| cs-b029 | 事实题 | 中 | 使用多线程而非多进程的两个主要动机是什么？ | threads-intro.pdf p3 为何使用线程 |
| cs-b030 | 事实题 | EN | What is a race condition? Explain using the example of a shared counter variable. | threads-intro.pdf p11 竞态条件 |
| cs-b031 | 事实题 | 中 | 临界区（critical section）指的是什么代码？我们希望对临界区实现什么性质，以避免竞态条件？ | threads-intro.pdf p11 临界区与互斥 |
| cs-b032 | 事实题 | EN | Why might a single line of code like counter++ not be atomic? | threads-intro.pdf p9-p10 The Heart Of The Problem |
| cs-b033 | 计算题 | 中 | 在读-改-写三条指令模型（load到寄存器、寄存器加一、写回内存）下，两个线程各对同一个counter变量执行1000次自增、完全不加锁，counter最终值可能的范围是多少？（2026-07-20改用书中「三条指令」的具体表述重出，原版泛泛提"counter++"跟java-ch1-e2e.epub的共享可变状态讨论概念级碰撞，噪音从80%降到20%） | threads-intro.pdf p9-p11 竞态条件分析（推导题） |
| cs-b034 | 无答案题 | EN | How exactly do coroutines implement cooperative switching between multiple execution flows within a single thread? | threads-intro.pdf（本章及本次ingest全部语料均未涉及协程coroutine，coroutine/green thread/async/fiber在整个语料库里均0命中） |

## threads-api.pdf（6 条，2026-07-20用cs-eval库真实审查过；3条英文/3条中文，中英各类型均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b035 | 事实题 | EN | What are the four parameters of pthread_create()? | threads-api.pdf p1 Thread Creation |
| cs-b036 | 事实题 | 中 | pthread_join() 的作用是什么？是否所有多线程程序都必须调用它？ | threads-api.pdf p2-p3, p5 Thread Completion |
| cs-b037 | 事实题 | EN | When waiting on a condition variable, why does the book recommend rechecking the condition in a while loop instead of using a one-time if check? | threads-api.pdf p8 One Last Oddity |
| cs-b038 | 事实题 | 中 | POSIX 线程库提供了哪两种初始化互斥锁（mutex）的方式？ | threads-api.pdf p6 Locks 初始化 |
| cs-b039 | 计算题 | 中 | 以下加锁代码有两处问题，分别是什么？ pthread_mutex_t lock; pthread_mutex_… | threads-api.pdf p6 Locks（破损示例代码分析） |
| cs-b040 | 无答案题 | EN | If multiple threads mostly just read shared data and rarely write to it, how exactly does pthread's read-write lock (rwlock) let multiple readers hold the lock at the same time and only enforce exclusion when a writer needs it? | threads-api.pdf（本章及本次ingest全部语料均未涉及读写锁rwlock，rwlock/read-write lock/reader-writer在整个语料库里均0命中） |

## vm-paging.pdf（9 条，2026-07-20用cs-eval库真实审查过；5条英文/4条中文，中英各类型均有覆盖；cs-b048由无答案题改判为事实题，原ground truth已矛盾）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b041 | 事实题 | EN | In paging, what is the difference between a page and a page frame? | vm-paging.pdf p1-p2 A Simple Example |
| cs-b042 | 事实题 | 中 | 一个虚拟地址在分页系统中如何被划分为 VPN 和 offset？ | vm-paging.pdf p3 地址结构 |
| cs-b043 | 事实题 | EN | What is the role of the valid bit in a page table entry (PTE)? | vm-paging.pdf p6 What's In The Page Table |
| cs-b044 | 事实题 | 中 | 为什么书中说最朴素的分页机制会让内存访问变慢？ | vm-paging.pdf p8-p9 Paging: Also Too Slow |
| cs-b045 | 事实题 | EN | What fragmentation-related advantage does paging have over previous approaches like segmentation, and why? | vm-paging.pdf p12 Summary |
| cs-b046 | 计算题 | 中 | 系统使用 32 位虚拟地址，页大小 4KB（2^12 字节），按书中地址划分方法，VPN 占多少位？页表最多需… | vm-paging.pdf p3 地址划分方法（推导题） |
| cs-b047 | 计算题 | EN | Following the same style as the book's example: 64-byte virtual address space, 16-byte pages, virtual address 21 (binary 010101) — VPN/offset and physical address given PFN=5? | vm-paging.pdf p3-p4 地址转换示例（沿用书中数值；2026-07-29自动GPU路径模型热身后连续3次正确作答） |
| cs-b048 | 事实题（原无答案题，已改判） | 中 | 为什么页表不直接存放在 MMU 芯片上的专用硬件里，而是存放在内存中？书中提到的最简单的页表组织形式是怎样工作的？ | vm-paging.pdf p6 页表的存放位置与组织方式 |
| cs-b058 | 无答案题 | EN | To avoid paying the extra memory access needed to walk the page table on every single memory reference, does the hardware use a small on-chip cache that holds recently used virtual-to-physical translations, and if so, how does it decide when a cached translation can still be reused versus when it needs to be re-fetched from the page table? | vm-paging.pdf（全文未讲解TLB工作原理；"TLB"/"Translation Lookaside Buffer"在vm-paging.pdf全文0命中，仅在cpu-sched.pdf、cpu-sched-multi.pdf各一笔带过） |

## vm-segmentation.pdf（7 条，2026-07-20用cs-eval库真实审查过；3条英文/4条中文，中英各类型均有覆盖；cs-b055的ground truth修正为no_location_expected，题目本身保留）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b049 | 事实题 | EN | How does the segmentation mechanism perform address translation? Under what circumstances does it trigger a segmentation fault? | vm-segmentation.pdf p1-p4 地址转换与 Segmentation Fault |
| cs-b050 | 事实题 | 中 | 分段机制会产生什么类型的碎片？书中是如何描述这一问题的？ | vm-segmentation.pdf p9 Managing Free Space |
| cs-b051 | 事实题 | EN | Which segments does a segmented system typically divide a process's address space into? | vm-segmentation.pdf p1-p2 Segmentation: Generalized Base/Bounds（见"遇到的问题"新增条目——中文版曾出现"堆段"被错答成"静态数据段"，英文版未复现） |
| cs-b052 | 事实题 | 中 | 分段相比之前整个地址空间用一对 base+bounds 映射的方式，解决了什么问题？ | vm-segmentation.pdf p1 引言 |
| cs-b053 | 计算题 | EN | Using the same code segment configuration as the book's Figure 16.3 (base=32KB, bounds/size=2KB), is an access at virtual offset=100B legal? What is the physical address? | vm-segmentation.pdf p3 Figure 16.3 Segment Register Values |
| cs-b054 | 无答案题 | 中 | 在现代x86-64处理器里，分段寄存器具体是怎么被实际使用的？ | vm-segmentation.pdf（本章只介绍经典分段概念与历史，未涉及 x86-64 具体实现；见"遇到的问题"——去掉元提问模板后仍然是严重幻觉，换了一套完全不同的编造内容） |
| cs-b055 | 无答案题 | 中 | 针对外部碎片问题，最佳适应（best-fit）和最差适应（worst-fit）这两种算法相比，具体的性能表现差多少？ | vm-segmentation.pdf p9（提到存在很多算法及压缩 compact 的思路，但未给出具体算法的量化对比数据） |

## 音频 segment-01（5 条，2026-07-20用cs-eval库真实审查过；打包后chunk边界（issue #10修复后，68碎片→5个大chunk）已核实仍完整覆盖各题所需时间戳内容，回答全部准确/合理）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-a01 | 音频题 | 中 | Remzi用top命令查看自己的机器时，系统里一共有多少个进程？其中真正处于活跃运行状态的有几个，其余大多数在做什么？ | 音频 segment-01 01:14–01:41（打包后位于segment-01.mp3/0001） |
| cs-a02 | 音频题 | 中 | cpu.c 中的 spin 函数为什么要重复调用 getTime，而不是写一个真正的空循环？ | 音频 segment-01 03:16–03:38（打包后与cs-a03同位于segment-01.mp3/0002） |
| cs-a03 | 音频题 | 中 | top 输出中进程 ID 0 是什么？它是什么时候创建的，负责什么？ | 音频 segment-01 02:19–02:49（打包后与cs-a02同位于segment-01.mp3/0002） |
| cs-a04 | 计算题 | 中 | 运行两个 cpu.c 实例后，系统空闲率变为约 50%。据此推断该机器有多少个虚拟核心？ | 音频 segment-01 04:07–04:29（打包后位于segment-01.mp3/0003） |
| cs-a05 | 无答案题 | 中 | Remzi用top命令查看进程信息时，具体展示了哪些内存统计数据？ | 音频 segment-01（全段均无内存数据细节，原文明确说"memory stats, which we are not going to look at at all"） |

## java-ch1-e2e.epub（10 条，新增，2026-07-20用cs-eval库真实审查过；4条英文/6条中文；仅覆盖epub第1章内容，事实题/计算题/无答案题均有覆盖）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b059 | 事实题 | 中 | 是哪两个迫切需求催生了Java 8的整套新特性？ | java-ch1-e2e.epub §1.1 为什么要关心Java的变化（见"遇到的问题"——核心chunk稳定排第1，但两次独立测试一次答对一次答错，是生成环节本身的不稳定，跟题目措辞无关） |
| cs-b060 | 事实题 | 中 | Stream API的加入，直接导致Java 8同时引入了哪两项配套功能？ | java-ch1-e2e.epub §1.1 为什么要关心Java的变化 |
| cs-b061 | 事实题 | EN | The book compares Stream to Unix pipe commands like cat/tr/sort/tail. What point about how Stream processes data is this analogy meant to illustrate? | java-ch1-e2e.epub §1.2.2 流处理 |
| cs-b062 | 事实题 | 中 | 方法引用（如 File::isHidden）相比 Java 8 之前用 FileFilter 匿名类实现同样的筛选功能，好处是什么？ | java-ch1-e2e.epub §1.3.1 方法和Lambda作为一等值（见"遇到的问题"新增条目——回答额外补充了书中未提及的"性能提升""类型安全"两点） |
| cs-b063 | 事实题 | EN | Why is the absence of shared mutable data a precondition for Stream's "almost free parallelism" to actually work? | java-ch1-e2e.epub §1.2.4 并行与共享的可变数据；图1-5示例 |
| cs-b064 | 事实题 | 中 | Optional<T> 是为了解决Java中的什么经典问题而引入的？ | java-ch1-e2e.epub §1.6 来自函数式编程的其他好思想 |
| cs-b065 | 事实题 | 中 | Java 8引入默认方法（default method），是为了解决接口演化过程中的什么困境？ | java-ch1-e2e.epub §1.5 默认方法及Java模块 |
| cs-b066 | 计算题 | 中 | 书中举的两个线程同时对共享变量sum加数的例子里，sum初始值为100，线程1执行sum=sum+3，线程2执行sum=sum+5。如果没有竞态条件、按顺序正确执行这两次加法，sum最终应该是多少？ | java-ch1-e2e.epub §1.2.4 并行与共享的可变数据；图1-5示例 |
| cs-b067 | 无答案题 | EN | How does Stream's reduce operation actually combine multiple elements into a single result? | java-ch1-e2e.epub（第1章只在提到filter类操作时顺带点名map、reduce这两个词，未展开解释具体机制） |
| cs-b068 | 无答案题 | EN | If a class implements multiple interfaces that each provide a default method with the same signature, what specific rule does Java use to resolve the conflict? | java-ch1-e2e.epub（第1章只说"Java 8用一些限制来避免出现类似于C++中臭名昭著的菱形继承问题"，未展开具体规则） |

## 图片题（3 条，新增，2026-07-20用cs-eval库真实审查过；1条无答案题）

| ID | 类型 | 语言 | 问题 | 来源定位 |
|---|---|---|---|---|
| cs-b069 | 无答案题 | 中 | RAG新闻分析报告流程里，"Core RAG"和"Ranking"两个阶段具体各自用的是哪个AI模型？ | 图片 cs_p1.png（图中只有流程步骤和挑战/建议文字，全程未提及任何具体AI模型名称） |
| cs-b070 | 事实题 | 中 | 大语言模型训练过程中的强化学习（RLHF）阶段，具体是通过什么方式让模型的回答更符合人类偏好的？ | 图片 cs_p2.png 第6步「强化学习（RLHF）」 |
| cs-b071 | 事实题 | EN | DeepMind's Nature cover article used graph neural networks to speed up optimization for proving or refining what kind of mathematical problems? | 图片 cs_p3.png 正文第二段 |
