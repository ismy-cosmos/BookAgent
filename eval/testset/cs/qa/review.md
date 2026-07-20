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

## threads-api.pdf（6 条）

| ID | 类型 | 问题 | 来源定位 |
|---|---|---|---|
| cs-b035 | 事实题 | pthread_create() 的四个参数分别是什么？ | threads-api.pdf p1 Thread Creation |
| cs-b036 | 事实题 | pthread_join() 的作用是什么？是否所有多线程程序都必须调用它？ | threads-api.pdf p2-p3, p5 Thread Completion |
| cs-b037 | 事实题 | 使用条件变量等待某个条件时，为什么书中建议用 while 循环重新检查条件，而不是用一次性的 if 判断？ | threads-api.pdf p8 One Last Oddity |
| cs-b038 | 事实题 | POSIX 线程库提供了哪两种初始化互斥锁（mutex）的方式？ | threads-api.pdf p6 Locks 初始化 |
| cs-b039 | 计算题 | 以下加锁代码有两处问题，分别是什么？ pthread_mutex_t lock; pthread_mutex_… | threads-api.pdf p6 Locks（破损示例代码分析） |
| cs-b040 | 无答案题 | threads-api 这章详细讲解了读写锁（pthread_rwlock）的使用吗？ | threads-api.pdf（本章只讲 mutex 与 condition variable 基本 API，未提及读写锁） |

## vm-paging.pdf（8 条）

| ID | 类型 | 问题 | 来源定位 |
|---|---|---|---|
| cs-b041 | 事实题 | 分页机制中页（page）和页帧（page frame）的区别是什么？ | vm-paging.pdf p1-p2 A Simple Example |
| cs-b042 | 事实题 | 一个虚拟地址在分页系统中如何被划分为 VPN 和 offset？ | vm-paging.pdf p3 地址结构 |
| cs-b043 | 事实题 | 页表项（PTE）中有效位（valid bit）的作用是什么？ | vm-paging.pdf p6 What's In The Page Table |
| cs-b044 | 事实题 | 为什么书中说最朴素的分页机制会让内存访问变慢？ | vm-paging.pdf p8-p9 Paging: Also Too Slow |
| cs-b045 | 事实题 | 书中总结部分指出，分页相比之前的方案（如分段）有什么碎片方面的优势？为什么？ | vm-paging.pdf p12 Summary |
| cs-b046 | 计算题 | 系统使用 32 位虚拟地址，页大小 4KB（2^12 字节），按书中地址划分方法，VPN 占多少位？页表最多需… | vm-paging.pdf p3 地址划分方法（推导题） |
| cs-b047 | 计算题 | 仿照书中例子：虚拟地址空间 64 字节、页大小 16 字节，虚拟地址 21（二进制 010101）对应的 VP… | vm-paging.pdf p3-p4 地址转换示例（沿用书中数值） |
| cs-b048 | 无答案题 | vm-paging 这章详细介绍了多级页表（multi-level page table）的具体实现吗？ | vm-paging.pdf（本章只用线性页表举例，p6 明确说更高级的数据结构留待后续章节） |

## vm-segmentation.pdf（7 条）

| ID | 类型 | 问题 | 来源定位 |
|---|---|---|---|
| cs-b049 | 事实题 | 分段（segmentation）机制如何进行地址转换？什么情况下会触发段错误（segmentation fau… | vm-segmentation.pdf p1-p4 地址转换与 Segmentation Fault |
| cs-b050 | 事实题 | 分段机制会产生什么类型的碎片？书中是如何描述这一问题的？ | vm-segmentation.pdf p9 Managing Free Space |
| cs-b051 | 事实题 | 分段系统通常将进程地址空间划分为哪几个段？ | vm-segmentation.pdf p1-p2 Segmentation: Generalized Base/Bounds |
| cs-b052 | 事实题 | 分段相比之前整个地址空间用一对 base+bounds 映射的方式，解决了什么问题？ | vm-segmentation.pdf p1 引言 |
| cs-b053 | 计算题 | 沿用书中 Figure 16.3 的代码段配置（base=32KB，bounds/size=2KB），若访问虚… | vm-segmentation.pdf p3 Figure 16.3 Segment Register Values |
| cs-b054 | 无答案题 | vm-segmentation 这章讨论了现代 x86-64 处理器中分段寄存器的实际使用方式吗？ | vm-segmentation.pdf（本章只介绍经典分段概念与历史，未涉及 x86-64 具体实现） |
| cs-b055 | 无答案题 | vm-segmentation 这章给出了不同外部碎片消减算法（如最佳适应、最差适应）的量化性能对比实验数据吗… | vm-segmentation.pdf p9（提到存在很多算法及压缩 compact 的思路，但未给出具体算法的量化对比数据） |

## 音频 segment-01（5 条）

| ID | 类型 | 问题 | 来源定位 |
|---|---|---|---|
| cs-a01 | 音频题 | 在这段 demo 开始时，Remzi 的机器上共有多少个进程？其中处于活跃运行状态的有几个？其余的在做什么？ | 音频 segment-01 01:14–01:41 |
| cs-a02 | 音频题 | cpu.c 中的 spin 函数为什么要重复调用 getTime，而不是写一个真正的空循环？ | 音频 segment-01 03:16–03:38 |
| cs-a03 | 音频题 | top 输出中进程 ID 0 是什么？它是什么时候创建的，负责什么？ | 音频 segment-01 02:19–02:49 |
| cs-a04 | 计算题 | 运行两个 cpu.c 实例后，系统空闲率变为约 50%。据此推断该机器有多少个虚拟核心？ | 音频 segment-01 04:07–04:29 |
| cs-a05 | 无答案题 | 在这段 demo 中，Remzi 用 top 查看了哪些内存统计数据？ | 音频 segment-01（全段均无内存数据细节） |

