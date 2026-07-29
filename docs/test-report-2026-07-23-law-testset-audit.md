# 法学测试集构建：真实管线审查记录

记录构建`eval/testset/law/qa/qa.jsonl`过程中，用真实端到端管线（`book_id=law-eval`，`answer()`，`qwen3:q4km`）对每道题的检索质量核验结果。审查方法：`eval/audit_question.py --subject law`跑真实`answer()`，逐个citation核对`score`（ChromaDB cosine距离，越小越相关）和chunk全文是否真能推出标准答案。

格式：每题按"题目原文+检索query+score表格+回答是否准确+具体分析"记录。跨题目的共性问题统一放本文档最后，不为这些问题单独开GitHub issue——如果问题本身跟issue #40（retrieve无相关性阈值）、issue #60（MAX_ROUNDS_EXCEEDED）已覆盖的范围一致，就不重复开。

全量结果汇总表（含Hit@5/工具调用/回答准确/幻觉四项指标）待全部批次审查完成后统一汇总，不按批次分别计算，避免中间数字被当作最终结论引用。

## chapter-02~05.pdf 章节：第一版flashcard式题目已弃用

批次1最初写成"In [案名], what did the Court hold"这种flashcard式提问（8道题实测7/8准确，记录曾短暂留存于本文档），被用户判定为纯记忆型考题、质量不合格后已弃用，题目原文不再赘述。

## chapter-02~05.pdf 章节：第二版自然场景题（当前qa.jsonl实际内容，2026-07-23）

**背景**：为解决flashcard式提问质量问题，把8道题改写成第一人称真实场景（隐去案名），实测**8道题里4道产生真实错误**（结论方向反了2道、跳过检索1道、`MAX_ROUNDS_EXCEEDED`无输出1道），相比flashcard版7/8准确明显更差。以下按当前`eval/testset/law/qa/qa.jsonl`里的题目原文逐题记录真实管线结果。

### law-b001（对应Katz v. United States，电话亭窃听）

**题目**（EN）："If the police, without getting a warrant, attach a listening device to the outside of a public phone booth and record everything a person inside says on a call — but never physically enter or tamper with the booth itself — have they conducted a search under the Fourth Amendment?"

**检索query**（模型自动生成，与题目原文不同）："Fourth Amendment definition and what constitutes a 'search' including electronic surveillance without physical entry"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-03.pdf/p0008/0013`（Kyllo判决里逐字引用Harlan的Katz测试） | 0.2853 | **能，核心论据** |
| `chapter-02.pdf/p0001/0000`（第四修正案条文全文+本章开篇介绍） | 0.3179 | 部分能 |
| `chapter-18.pdf/p0015/0029`（*Camara*行政搜查案，跨章节无关） | 0.3202 | 不能 |
| `chapter-02.pdf/p0013/0024`（Alito协同意见讨论trespass理论历史） | 0.3271 | 部分能 |
| `chapter-05.pdf/p0003/0004`（Carpenter判决回顾Katz历史脉络） | 0.3319 | 部分能 |

**回答是否准确：准确**。正确引用Katz确立的"合理隐私期待"测试得出"构成搜查"的结论，并额外援引*Silverman v. United States*（插入麦克风入墙案）做类比论证（这个案例不在检索到的5个chunk里，应为模型自身训练知识补充，但论证方向和结论都正确、未产生误导）。

**具体分析**：真实检索到的核心chunk（Harlan测试在Kyllo判决里的复述）虽不是`supporting_chunks`标注的原始出处，但同一测试原话的重复出现让回答依然准确。这道题去掉案名后检索质量未受明显影响，因为"public phone booth"+"listening device"这些具体场景词本身就是很强的检索锚点。

### law-b002（对应United States v. Jones，GPS追踪器）

**题目**（EN）："If police, without a warrant, secretly attach a GPS tracker to the underside of someone's car while it's parked in a public lot, then use it to log the car's location continuously for a month, is that a Fourth Amendment search?"

**检索query**：'Fourth Amendment and warrantless installation of GPS tracker on vehicle'

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-02.pdf/p0012/0023`（Alito协同意见，质疑多数意见trespass理论） | 0.2673 | 部分能 |
| `chapter-02.pdf/p0016/0029`（Alito协同意见，论证长期监控问题） | 0.3028 | 部分能 |
| `chapter-02.pdf/p0014/0026`（Alito协同意见，批评trespass理论的具体缺陷） | 0.3201 | 部分能 |
| `chapter-02.pdf/p0007/0011`（案件事实：GPS安装+28天追踪经过） | 0.3207 | 能 |
| `chapter-02.pdf/p0018/0031`（章节小结，引出下一章Carpenter案） | 0.3281 | 部分能 |

**回答是否准确：结论正确，但说理角度有误**。回答正确得出"构成搜查"，但论证主线落在"长期追踪（一个月）侵犯隐私期待"——这实际是Alito协同意见的mosaic理论，不是本案多数意见（Scalia）真正采用的trespass理论（"政府为获取信息而物理占用私人财产本身即构成搜查，不需要证明违反合理隐私期待，也不取决于监控时长"）。

**具体分析**：检索到的5个chunk里4个来自Alito协同意见，标注的`supporting_chunks`（`chapter-02.pdf/p0007/0012`，多数意见"The Government physically occupied private property..."原句）没有进入检索结果，导致模型只看到协同意见的论证材料、据此重构了一个说理角度有偏差但结论碰巧正确的回答。

### law-b003（对应California v. Greenwood，路边垃圾翻查）—— **错误**

**题目**（ZH）："警察怀疑我贩毒，但没有申请搜查令，直接联系收垃圾的工人，把我放在自家门前路边、等着被收走的垃圾袋要过来翻查，这样做侵犯了我受第四修正案保护的隐私吗？"

**检索query**（模型自动生成，未提取"垃圾"这一关键场景词）："美国宪法第四修正案关于搜查和扣押的规定，以及警察在没有搜查令的情况下进行搜查是否合法"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-09.pdf/p0003/0006`（Aguilar案：中立法官签发令状原则，跨案无关） | 0.2761 | 不能 |
| `chapter-21.pdf/p0003/0004`（Terry stop合理怀疑标准，跨案无关） | 0.2864 | 不能 |
| `chapter-19.pdf/p0021/0040`（逮捕后附带搜查规则，跨案无关） | 0.2917 | 不能 |
| `chapter-02.pdf/p0001/0000`（第四修正案条文全文，泛泛相关） | 0.2979 | 不能 |
| `chapter-33.pdf/p0018/0030`（毒果树理论/衰减原则，跨案无关） | 0.3007 | 不能 |

**回答是否准确：不准确，结论方向完全相反**。回答认定"警察的行为侵犯了您受第四修正案保护的隐私权"，而根据Greenwood案的真实holding，路边等待清运的垃圾袋已经暴露给公众、且是当事人主动转交给第三方垃圾工，不享有受保护的隐私期待，警察此举**不构成侵犯**。

**具体分析**：检索到的5个chunk里**没有一个与Greenwood案或垃圾翻查有任何关系**——问题出在模型自己生成的检索query本身就是一个通用的"警察无证搜查是否合法"提问，完全没有带入题干里"垃圾""路边""收垃圾工人"这些本该是最强检索锚点的具体场景词。检索完全落空后，模型转向一般性的"无证搜查+无例外情形=违法"的通用法律逻辑作答，得出了跟真实判例相反的结论。这暴露的是模型生成检索query时自行做了抽象化（把具体场景抽象成"警察无证搜查是否合法"这一泛化问题），反而丢失了最关键的检索线索。

### law-b004（对应Kyllo v. United States，热成像扫描）—— **已修复，稳定**

**题目**（ZH，最终版）："警察怀疑我在家里种大麻，虽然没有踏入我家一步，但用一台**市面上普通人根本买不到、只有执法部门才配备**的专业热成像设备，从街对面的车里扫描我家外墙，检测出屋顶和一侧墙壁的温度明显偏高，以此为线索申请到了搜查令。这种隔着距离扫描热量分布、**且这类设备一般公众根本无法获取**的做法，算不算搜查？"

**检索query**："热成像设备在执法中的使用是否构成搜查"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-03.pdf/p0013/0021`（同时包含"当时不属于一般公众使用"这一历史标准+"现在FLIR ONE已经民用普及"的现状讨论） | 0.3877 | 能，核心论据（但也是容易带偏结论的一条） |
| `chapter-03.pdf/p0007/0011`（案件事实：Agema Thermovision 210扫描经过） | 0.4209 | 部分能 |
| `chapter-03.pdf/p0012/0019`（Stevens异议：隐私利益微不足道的论证） | 0.4273 | 不能，异议观点 |
| `chapter-03.pdf/p0007/0012`（案件程序历史：地区法院/上诉法院裁决） | 0.4282 | 不能 |
| `chapter-03.pdf/p0009/0015`（**Scalia多数意见**：拒绝把"是否搜查"限定在"intimate details"，正是本案核心论证） | 0.4283 | 能，多数意见核心论据 |

**回答是否准确：准确**。结论"构成搜查"。模型正确处理了`p0013/0021`里"当时不公开"和"现在已经普及"这两条容易混淆的信息，区分"Kyllo案本身的技术公开程度"和"题目里这台设备本身就是执法专用、公众无法获取"是两件不同的事，没有被现代热成像设备普及这一点带偏，也没有把`p0012/0019`（Stevens异议）误认成多数意见。经`audit_question.py`多次复测+真实后端API复测，结果一致。

**具体分析**：这道题原本的flashcard版题面（"用一台热成像仪…"，未锚定设备的公众可及性）实测下来，模型会把检索到的多数意见（`p0009/0015`）和异议意见搞混，得出相反结论——根源是题目本身没有锚定"设备是否一般公众可及"这个Kyllo测试的决定性事实，模型按"现在"技术普及程度判断，对一道表述不清的题目给出了看似合理但错误的回应。题目重写锚定这一决定性事实后，问题解决。

### law-b005（对应Smith v. Maryland，电话号码记录器）

**题目**（EN）："If police ask the phone company to install a device at the phone company's own switching facility that just logs which numbers I dial from my home phone — not the content of the calls — and they do this without a warrant, have they conducted a search?"

**检索query**："whether installing a device at a phone company's switching facility to log dialed numbers constitutes a search under the Fourth Amendment"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-03.pdf/p0018/0029`（案件背景：pen register定义+案发经过） | 0.3342 | 部分能 |
| `chapter-03.pdf/p0019/0030`（**逐字包含核心holding原句**："...the Court of Appeals affirmed the judgment of conviction, holding that 'there is no constitutionally protected reasonable expectation of priv[acy]...'"） | 0.3584 | **能，核心论据（此前标注"部分能"是错误的，已订正）** |
| `chapter-05.pdf/p0001/0000`（第5章开篇回顾Smith案，跨章节但相关） | 0.3680 | 部分能 |
| `chapter-02.pdf/p0012/0023`（Jones案Alito协同意见，跨案无关） | 0.3727 | 不能 |
| `chapter-05.pdf/p0001/0001`（Carpenter判决开篇引出Smith案对比） | 0.3762 | 部分能 |

**回答是否准确：准确**。正确得出"不构成搜查"，逐字引用了pen register真实判决语句（"there is no constitutionally protected reasonable expectation of privacy in the numbers dialed..."），并正确提及Carpenter案后续如何区分处理CSLI数据。

**具体分析（已订正）**：标注的`supporting_chunks`（`chapter-03.pdf/p0020/0032`）没有进入top-5，但排名第2的`p0019/0030`本身就**逐字包含核心holding语句**（只是被截断在"priv"这个词中间）——这次是真实的Hit@5成功，此前把这个chunk标成"部分能"是我核对不仔细导致的错误标注，用户指出后复核确认已订正。

### law-b006（对应United States v. Oliver，开放田地）—— **已修复，稳定**

**题目**（EN，最终版）："I own a large stretch of farmland about a mile from my house. I've fenced the whole area and posted \"No Trespassing\" signs all around it. If police walk onto that land without a warrant or my permission to look for evidence of a crime — does the constitutional protection against unreasonable government searches and seizures of a person's \"houses, papers, and effects\" extend to open land like this, or is it outside that protection? Would police doing this violate my rights?"

**检索query**："Fourth Amendment protection for open land vs. private property with fencing and 'No Trespassing' signs"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-04.pdf/p0002/0002`（Sixth Circuit判决理由：Hester原则与Katz隐私标准兼容） | 0.2837 | 能 |
| `chapter-04.pdf/p0003/0004`（历史沿革：Holmes在Hester案的普通法区分） | 0.2906 | 能，核心论据 |
| `chapter-04.pdf/p0001/0000`（第四修正案文本范围引入，区分curtilage/open fields） | 0.3012 | 能，背景论据 |
| `chapter-04.pdf/p0004/0005`（承接common law讨论，明确肯定Oliver案结论） | 0.3035 | 能 |
| `chapter-04.pdf/p0003/0003`（**正是`supporting_chunks`标注的原始出处**：判断开放田地是否受保护的考量因素） | 0.3354 | **能，核心论据** |

**回答是否准确：准确**。开放田地不受第四修正案保护，即使有围栏和"禁止进入"标志也一样，正确提及了Marshall/Brennan/Stevens的异议意见、没有与多数意见混淆。经`audit_question.py`多次复测+真实后端API复测（用户独立复测确认一致），结果稳定。

**具体分析**：这道题原本的flashcard版题面（"If I own a large piece of farmland...can police walk onto that land without a warrant..."）实测下来模型判断"本题不涉及数值计算或书中具体内容"，全程零次调用retrieve，直接凭训练知识给出一般性、笼统的错误回答。系统提示词修改（见下方"系统提示词改动"一节）后，稳定触发retrieve，`supporting_chunks`标注的原始chunk（`p0003/0003`）真实进入top5，问题解决。

### law-b007（对应United States v. Dunn，谷仓附属地）—— **明显改善，方向正确但结论较含糊；用户真实后端复测5次结果稳定**

**题目**（ZH）："警察没有搜查令，跨过我家周围的围栏，又跨过好几层内部的铁丝网围栏，走到我家谷仓（离住宅50码，前部本身也用围栏围起来、装了门）门口，透过门上网眼用手电筒往里照，看到了像是在制毒的场景。谷仓离我住宅这么远，这个区域算是我住宅受保护的"附属地"（curtilage）吗？警察这样做侵犯我的隐私了吗？"

**检索query**："美国宪法第四修正案下住宅的curtilage定义及范围"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-04.pdf/p0001/0000`（第四修正案文本范围引入，区分curtilage/open fields） | 0.3024 | 部分能，背景论据 |
| `chapter-04.pdf/p0003/0004`（历史沿革：Holmes在Hester案的普通法区分） | 0.3095 | 部分能 |
| `chapter-09.pdf/p0023/0040`（Collins案汽车例外，跨案但相关） | 0.3126 | 不能 |
| `chapter-04.pdf/p0018/0028`（Riley案直升机航拍讨论） | 0.3127 | 不能 |
| `chapter-04.pdf/p0005/0006`（第四修正案范围的一般性讨论） | 0.3140 | 不能 |

**回答是否准确：方向正确，但结论较含糊，不像标准答案那样干脆**。回答正确列出Dunn案判断curtilage的四要素（距离/围栏/用途/防观察措施），结论为"谷仓离住宅50码且有多层围栏，很可能不被视为附属地……警察……可能不构成对第四修正案的侵犯"——方向对，但用"很可能""可能"这类保留措辞，不是标准答案那样确定的结论。经真实后端API复测（含用户独立复测5次），结果稳定一致。

**`supporting_chunks`标注纠错（2026-07-23）**：原先标注的`chapter-04.pdf/p0007/0009`**本身就是错的**——实际读取该chunk全文，内容是纯案件事实叙述（谷仓离围栏50码、离住宅60码等具体细节，正是此前`calculate`误触发那次"50+60=110"的数字真实出处），完全不包含四要素的任何表述。真正给出四要素完整原文的是**`chapter-04.pdf/p0007/0010`**（"we believe that curtilage questions should be resolved with particular reference to four factors: the proximity of the area claimed to be curtilage to the home, whether the area is included within an enclosure surrounding the home, the nature of the [use]..."，后面还逐条把四要素适用到本案事实上）——这个chunk在多次复测里其实都被检索到过，此前一直核对的是错误的chunk ID，误以为"官方四要素chunk从未命中"。已将`qa.jsonl`里`law-b007`的`supporting_chunks`订正为`chapter-04.pdf/p0007/0010`。

**具体分析**：这道题从系统提示词修改前"4轮检索均无关键chunk、耗尽轮次、`MAX_ROUNDS_EXCEEDED`完全无输出"，改善为"给出真实、方向正确的回答"。`audit_question.py`早期复测中曾观察到少数样本（结论方向错误、以及误触发`calculate`工具算"50+60=110"）不稳定的情况，这些异常在后续用真实后端API的复测中没有复现；`calculate`误触发单独记录为issue #64，不影响这里的回答准确性判断。

### law-b008（对应Carpenter v. United States，手机基站定位记录）

**题目**（ZH）："警察怀疑我参与了几起持械抢劫案，没有搜查令，直接找我的手机运营商调取了我127天的历史基站定位记录，用来证明案发时我人在案发地点附近。运营商保存这些记录本来就是出于自己的商业目的，警察这样调取算不算侵犯了我受第四修正案保护的隐私？"

**检索query**："美国宪法第四修正案关于搜查和扣押的规定，特别是涉及电子通信数据（如基站定位记录）的合法性要求"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-41.pdf/p0012/0019`（FISA涉外情报监控条款，跨章节无关） | 0.3373 | 不能 |
| `chapter-05.pdf/p0007/0009`（Carpenter判决结论："第三方持有不减损第四修正案保护"） | 0.3579 | **能，核心论据** |
| `chapter-14.pdf/p0024/0042`（边境电子设备搜查案例，跨章节无关） | 0.3636 | 不能 |
| `chapter-05.pdf/p0003/0004`（Katz历史脉络回顾，背景相关） | 0.3645 | 部分能 |
| `chapter-02.pdf/p0012/0023`（Jones案Alito协同意见，跨案无关） | 0.3750 | 不能 |

**回答是否准确：准确**。正确得出"构成搜查"，逐字引用了Carpenter判决"政府获取无线运营商保存的手机基站位置记录，属于一种'搜索'行为，受第四修正案约束"这一核心结论。

**具体分析**：5个chunk里3个跨章节无关（FISA条款、边境搜查、Jones协同意见），真正命中的只有`p0007/0009`一个，但恰好是全案结论句，支撑了正确回答。这道题保留了"127天""持械抢劫""基站定位记录"等具体场景词，检索锚点仍然较强。

## 第二版批次小结（law-b001~008，系统提示词修改+题目重写后的最终状态，2026-07-23）

| 题号 | 对应判例 | 结果 |
|---|---|---|
| b001 | Katz（电话亭窃听） | 准确 |
| b002 | Jones（GPS追踪） | 结论正确，说理角度有误（协同意见当主线，未修复） |
| b003 | Greenwood（垃圾翻查） | **错误，结论方向相反**（检索query自我抽象化丢失场景锚点，未修复） |
| b004 | Kyllo（热成像） | **已修复，稳定**（题目重写锚定"设备是否公众可及"这一决定性事实+系统提示词修改） |
| b005 | Smith（电话号码记录器） | 准确 |
| b006 | Oliver（开放田地） | **已修复，稳定**（系统提示词修改后稳定触发retrieve、结论正确，用户真实复测确认） |
| b007 | Dunn（谷仓附属地） | **明显改善，方向正确但结论较含糊**（不再`MAX_ROUNDS_EXCEEDED`无输出；`supporting_chunks`原标注有误已订正，订正后的官方四要素chunk`p0007/0010`本身能被检索到；用户真实复测5次结果稳定） |
| b008 | Carpenter（基站定位记录） | 准确 |

8道题里7道准确/已修复（b001/b004/b005/b006/b007/b008 + b002方向正确），只有b003仍是真实、未解决的缺陷——模型自生成query把"垃圾"这个决定性场景细节抽象掉了，保留原样作为真实管线缺陷证据，暂无进一步改写计划。

## 系统提示词改动（2026-07-23，已提交）

排查b006"跳过检索"问题过程中，发现`pipeline/agent/client.py`的`_SYSTEM_PROMPT`虽然写了"用户主动问书里内容就必须调用retrieve，哪怕你觉得自己已经知道答案"，但没有堵住另一条路径：模型可以自己先判断"这个问题读起来像通用常识/常见法条问题，跟这本书无关"，从而完全不触发这条规则、直接跳过retrieve。b006、此前的law-b009（人脸识别无答案题）都属于这个模式。

修改内容：在`retrieve`说明后追加一句——

> "你对retrieve能查到的知识库里具体收录了什么内容、覆盖多大范围——没有任何先验信息（没有书名、目录、简介），不能仅凭问题读起来像"通用常识/常见法律法条问题"就判断这跟知识库无关而跳过检索，唯一能确认的办法是先调用retrieve看检索结果里有没有相关内容。"

真实管线验证结果（详见commit message，`git log`可查完整记录；`audit_question.py`多次复测+真实后端API复测+用户独立复测的综合结论）：
- **修复，稳定**：law-b004、law-b006（均经`audit_question.py`多次复测+真实后端API复测+用户独立复测确认，详见各自小节）
- **修复，稳定**：law-b009——2026-07-29自动GPU路径连续3次均为1次retrieve+完整披露资料不足，无截断，详见该题条目和总体统计
- **明显改善，方向正确但结论较含糊**：law-b007——从`MAX_ROUNDS_EXCEEDED`完全无输出变成给出真实、方向正确的回答，用户真实复测5次结果稳定；另外发现`supporting_chunks`原标注（`p0007/0009`）本身是错的（那是纯案件事实叙述，不含四要素），已订正为真正给出四要素原文的`p0007/0010`
- **间接改善，存在约1/8的真实反复**：clinical-b004——自生成retrieve query更贴近题目原文措辞，多数情况下（约7/8）命中目标chunk，但仍有约1/8概率退回旧版query、目标chunk未命中，详见clinical测试报告
- **基本未修复**：clinical-b036——追加复测后发现8次里7次仍是原来的无披露幻觉，只有1次诚实披露，最初判断"已修复"是只看了1个样本的误判，详见clinical测试报告
- **未修复**：cs-b014（semaphore）、cs-b023（MLFQ）、cs-b034（协程）、cs-b058（TLB）——这4道CS已知的"检索到不相关内容但仍自信编造"幻觉案例，复测后行为和原来几乎一字不差
- **回归检查无异常**：law-b001/b002/b003/b005/b008、cs-a01

综合来看，这条提示词修改对"该不该触发retrieve"这类决策边界问题效果确实、稳定（law-b004/b006），对"检索到内容后该不该继续重试"效果明显但不完美（law-b007），对issue #40真正核心的"检索到明确不相关内容后仍自信编造"这类幻觉模式基本没有触及（clinical-b036、CS四题）。

## 意外发现：calculate工具误触发（独立缺陷，未修复）

b007复测过程中，5次里出现1次模型自己把检索到的两个不相关数字（"谷仓离围栏50码"和"离住宅60码"——同一距离从两个不同参照点描述，不是可相加的两段路程）拼成算式调用了`calculate`工具，实测捕获到真实参数：`expression='50 + 60' -> '110'`，这个"110码"最终也没有被实际用于回答的结论推理，纯属多余。

核对过`_SYSTEM_PROMPT`原文，"只要**问题**涉及任何数值计算...都必须调用"这条规则本身限定的是"问题需要计算"，b007题目根本不涉及任何计算，规则字面上并不支持这次调用——是模型自己越权把"检索内容里出现了两个数字"泛化成了"需要计算"，不是提示词文本鼓励的行为。这是一个新发现的、独立于本次retrieve改动的缺陷，暂不处理，已记录（见issue追踪）。

## 温度0下的真实复现率（2026-07-23实测）

针对"温度已经是0，为什么同一题多次运行结果不一样"这个问题，做了精确测试而非泛泛归因于"随机性"：
- clinical-b056在2026-07-29自动GPU路径连续跑3次：retrieve query逐字相同，均为1次retrieve后完整披露资料不足；高层行为路径一致，但补充的通用药理文字并非逐字相同。
- law-b007连续跑5次：第一次retrieve的query 5次全部逐字相同；4/5次都是"1次retrieve、不调用calculate"，但这4次里具体回答的**文字表述本身并不完全一致**；1/5次在拿到第一次retrieve结果后走向了"继续查+误触发calculate"这条不同路径。
- clinical-b004（自生成query对比测试）：同一套提示词下连续跑3次，query文本逐字相同；换成另一套提示词后再连续跑3次，query文本又是另一句逐字相同的话——组内完全确定性、组间因提示词不同而不同，排除了"运气"这个解释。

结论：温度0在同一输入+同一环境下，多数情况和多数决策点确实是确定性的，但token级别的极细微数值噪声始终存在，多数时候不影响最终高层行为路径，少数时候会在某个具体决策token上翻到另一条路径——这跟Ollama/llama.cpp量化推理层面的浮点非结合性有关，不是"温度没设对"，也不是随机数种子的问题。

## 检索机制深挖（针对上述4道错误题的根因排查，2026-07-23）

**注**：以下排查基于系统提示词修改**之前**的原始错误结果，是诊断这些问题真实根因的过程记录。b004/b006/b007后续已通过系统提示词修改和/或题目重写修复（见上方"系统提示词改动"一节），这里的分析作为根因排查的历史记录保留，不代表当前最终状态。

用户对b002~b007的错误结果提出多个具体机制质疑，逐条用代码+真实探测验证如下（不是猜测）：

**1. 长篇讨论+50-token overlap是否包不住案名/多数-异议区分？**——确认属实。`pipeline/chunk/chunker.py`里`_MAX_TOKENS=512`、`_OVERLAP_TOKENS=50`；用真实embedder对b002原query在`law-eval`库里探测到top-20（不只是top-5），结果：Jones案多数意见那句最直接的holding原文（`chapter-02.pdf/p0007/0012`，"The Government physically occupied private property for the purpose of obtaining information"）**在top-20里完全没有出现**，反而Alito协同意见被检索到4次（`p0012/0023`第1、`p0016/0029`第2、`p0014/0026`第3等）。50 token的overlap只能桥接相邻chunk，桥接不了一个跨越十几个chunk的长篇判决讨论里"案名/多数意见"这类只在开头出现一次的标识信息。

**2. BM25+向量混合检索能解决这个问题吗？**——现状是本项目目前**没有任何BM25/关键词检索**，纯向量（`pipeline/store/chroma_store.py`用ChromaDB cosine距离）。但即使加上BM25，b002这种情况也解决不了：多数意见和协同/异议意见讨论同一问题用词高度重叠（都在反复出现"Fourth Amendment""search""trespass"），协同意见往往还写得更长、论证词汇更密集，BM25一样会给协同意见更高的词频分——BM25能解决的是b003那种"query本身漏掉了关键词"的问题（词确实在文档里但query没提），解决不了"两边都在用同一套词汇argue相反结论"的问题。

**3. b004是否存在"作者写的反面案例（异议意见）被当成事实检索到，评论没跟着包进同一个chunk"的情况？**——确认属实，且比原来记录的更严重。检索到的5个chunk里3个（`p0010/0017`、`p0012/0019`、`p0011/0018`）逐字核对后**全部是Stevens的异议意见**（论证off-the-wall热成像不构成搜查），真实的Kyllo多数意见（Scalia执笔，结论相反）的核心表述没有被检索到。更值得注意的是模型自己把这3个异议chunk错误标注成"多数意见（由大法官Scalia主持）"——这不是"没有异议标签跟着"的问题，是模型自己把标签安错了。

**4. b002这类"法院内部多数决、写了好几份意见"的题目，检索本身能否找到"最终判决"，我们的题目/提示词有没有引导模型认识到这一点？**——用户这个判断是对的。真实探测显示：即便扩大到top-20，Jones案多数意见那句最精确的holding原文都没有出现，检索到的全是协同/异议意见的论证片段。`pipeline/agent/client.py`里的系统提示词（`_SYSTEM_PROMPT`）**完全没有一句话提到"多份意见时优先采信majority opinion/法院最终判决"这类指导**，模型没有被告知要区分"法院意见"和"某位大法官的个人协同/异议意见"。这类题目本身确实比单一意见的案件更难保证有唯一"标准答案chunk"，后续出题应避免选内部意见分歧大、篇幅长的案件作为"事实题"的素材，或者题干里明确限定"法院最终多数意见"。

**5. b003是模型自身理解问题，而非检索能力问题——已用改进query验证**。用同一个embedder、同一个库，把原query（"美国宪法第四修正案关于搜查和扣押的规定，以及警察在没有搜查令的情况下进行搜查是否合法"——完全没提"垃圾"）换成带场景关键词的版本（"警察没有搜查令翻查放在路边等待清运的垃圾袋是否侵犯隐私"），检索结果从top-20全部跟Greenwood案无关，变成top-5里3个直接命中Greenwood案核心论证段落（`p0002/0002`正是`supporting_chunks`里标注的原始出处，`p0004/0005`、`p0005/0008`、`p0005/0007`都直接陈述"没有客观隐私期待"这个holding）。**检索能力本身没问题，问题出在模型自己生成retrieve query时把"垃圾"这个本题唯一的决定性事实给抽象掉了**——这跟用户说的一致：识别"审查对象是垃圾"这一点需要抓住场景里最关键的具体细节，这对人来说是直觉，但对一个把问题重新表述成通用法律问题的模型来说很容易被泛化掉。这类问题确实更适合定位成"检索query生成的通用弱点"，而不是可以靠换一种问法就稳定解决的东西。

**6. b005的retrieve query里出现"Fourth Amendment"，题目原文并没提，这个词是哪来的？**——核实`pipeline/agent/answer.py`全文没有任何地方把书名/书籍简介注入system prompt，`client.py`的`_SYSTEM_PROMPT`也是通用文本、不含任何书籍相关信息。所以"Fourth Amendment"不是上下文泄漏进来的，是模型自己从"warrant""search"这些词联想到宪法领域、主动把retrieve query扩写得更专业——这是模型自主生成检索query时正常的知识调用行为，不是bug。

**7. b005有一个chunk被我原先标错了**：`chapter-03.pdf/p0019/0030`原本标注"部分能"，用户追问后重新核对，这个chunk其实**逐字包含了核心holding原句**（"...holding that 'there is no constitutionally protected reasonable expectation of priv[acy]...'"，只是被截断在词中间）——这次实际上是真实的Hit@5命中，上面b005小节的表格和分析已订正。

**8. b006为什么模型完全跳过了retrieve？**——模型自己的原话是"Since the query is not about numerical calculations or specific content from a book, I will answer based on general legal knowledge"。推测机制：系统提示词要求"只要问题涉及书中内容...就必须调用retrieve"，但这条规则依赖模型自己判断"这是不是在问书里的内容"——一道完全自然的第一人称场景题（没有案名、没有"根据这本书"这类信号词）在模型看来更像一道通用司法考试题，而不是"针对这本特定书提问"，于是被模型自己归类成可以直接用训练知识回答的一般法律常识问题，没有触发retrieve的判断规则。这是纯自然场景题（尤其是去掉案名后）相对于flashcard式提问的一个真实、可复现的额外弱点。

**8.1 重新拟题验证（2026-07-23）**：按"场景保留、但把'第四修正案'换成条文实质内容、并加入'这项保护延伸到...吗'这种明显在问法律边界的措辞"重写了b006（题目原文见下方最终版qa.jsonl），重新跑`audit_question.py`后**依然是0次retrieve调用**，模型这次给出的回答内容碰巧是对的（主动提到了"Open Fields Doctrine"这个准确的法律术语，结论方向也跟标准答案一致），但依然完全没有查库，纯靠训练知识作答。这说明"跳过retrieve"这个问题跟措辞是否生活化关系不大——open fields doctrine本身是足够知名的宪法法条，无论怎么改场景措辞，只要不显式提示"请查阅本书"，模型大概率都会判断自己已经知道答案、不需要验证。这道题目前**保留现状**（不再继续改措辞硬修），作为"检索被完全跳过、纯靠训练知识蒙对"这一真实缺陷模式的证据。

**9. 关于"生产前端"和`audit_question.py`对同一题（以clinical-b056/hydralazine为例）给出不同结果的问题**：排查过程记录如下（结论几次反转，如实记录）。

- 第一步：早期把`clinical-b056`在`audit_question.py`（`clinical-eval`库）里连跑两次，两次的5次retrieve query逐字相同、都走到旧版`[MAX_ROUNDS_EXCEEDED]`；这是当时代码版本下的历史记录。
- 第二步：一开始怀疑是生产库`.chroma`（`book_id="clinical"`）跟评测库`.chroma-eval-clinical`（`book_id="clinical-eval"`）内容不同导致的——查`.chroma`发现`clinical`确实有686个chunk，`law`有1710个chunk，跟`clinical-eval`686个、`law-eval`1852个数字对不上，一度以为是两个不同库。
- 第三步：用户指出"文件是一模一样的"，重新核对：两个collection的`source_file`列表逐字相同、chunk数量都是686，同一个chunk_id（`openstax-pharm-ch18-antihypertensive.pdf/p0021/0096`）在两边的**content哈希完全一致**，用同一个embedder对同一个query在两边分别检索，top-10的chunk_id顺序和score（精确到小数点后6位）**完全相同**——第二步"两个库不同"的猜测是错的，已撤回。
- 当前结论（2026-07-29更新）：使用`Embedder()`自动GPU路径对clinical-b056连续复测3次，3次均为1次retrieve后完整披露资料不足，未再出现`MAX_ROUNDS_EXCEEDED`或输出截断；retrieve query和5个候选chunk保持一致。此前“隔离环境稳定复现`MAX_ROUNDS_EXCEEDED`”的记录不再代表当前代码状态，关于CPU query embedding候选换位的推测不再作为当前结论。

**10. b010当前前端结果的复核**——提示词改动后的前端运行已经明确写出“检索到的资料不足以判断这个具体问题”。这是正确的检索边界披露；但它随后又补入“美国部分州通常不需要事先同意”等通用法律说法。该补充不来自任何当前引用的chunk，因此不能当作基于本书的结论。现将旧的“无披露幻觉”记录覆盖为下方当前前端运行的完整记录。

**背景**：出题前已用关键词核实全库1852个chunk：`facial recognition`/`人脸识别`/`body camera`/`body-worn camera`/`执法记录仪`均为0命中，`taser`也是0命中。

### law-b009

**题目**（EN，无答案题）："When police use a facial recognition system to scan a crowd in a public place and match faces against a database of ID photos, do they need to obtain a warrant beforehand?"

**检索query**："legal requirements for police using facial recognition systems to scan crowds and match against ID photo databases"

| chunk | score | 能否支撑“公共场所人脸识别是否须先取得令状” |
|---|---:|---|
| `chapter-39.pdf/p0014/0025` | 0.43635743856430054 | 不能 |
| `chapter-38.pdf/p0014/0022` | 0.4394634962081909 | 不能 |
| `chapter-39.pdf/p0003/0005` | 0.4406375288963318 | 不能 |
| `chapter-39.pdf/p0006/0009` | 0.44062578678131104 | 不能 |
| `chapter-18.pdf/p0019/0038` | 0.4453390836715698 | 不能 |

**回答是否准确：准确披露资料不足，结果稳定。** 2026-07-29使用`Embedder()`自动GPU路径跑真实`answer()`连续3次，3次均只调用1次retrieve，均完整说明命中的指认程序、照片指认和DNA材料不能直接回答公共场所人脸识别是否需要令状；没有就该实体法问题作出确定结论，也没有输出截断。

**具体分析**：3次retrieve query逐字相同，均返回上表5个不相关chunk。回答会补充“可能涉及隐私或第四修正案”等一般背景，但每次都明确限定为当前资料不足以判断具体令状要求。因此本题当前应计为有效无答案题的正确披露；2026-07-24的截断输出不再作为当前结论。

### law-b010

**题目**（ZH，无答案题）："警方在讯问室里对嫌疑人全程佩戴执法记录仪（body camera）进行录像，这种录像行为本身是否需要事先取得嫌疑人的同意？"

**检索query**：2026-07-24 的前端会话未持久化工具调用 query；仅保留题目、回答和 citation。

| chunk | score | 能否支撑答案 |
|---|---|---|
| `chapter-28.pdf/p0014/0024`（*Pennsylvania v. Muniz*案中的录像证据可采性） | 0.3856062889099121 | 不能 |
| `carpenter-v-united-states-2017.mp3/0014`（手机定位记录讨论） | 0.393288254737854 | 不能 |
| `chapter-34.pdf/p0012/0017`（Miranda警告延迟出示的策略讨论） | 0.3945540189743042 | 不能 |
| `birchfield-v-north-dakota-2016.mp3/0037`（呼气测试令状实践讨论） | 0.4028775691986084 | 不能 |
| `chapter-27.pdf/p0006/0011`（讯问权利的一般讨论） | 0.4038165211677551 | 不能 |

**回答是否准确：核心披露准确，但整段回答不完全合格。** 模型先准确说明检索资料不足以判断这个具体问题；在现行“是否明确披露”口径下，不计为无披露幻觉。随后它又称部分州通常无须事先同意、并给出隐私例外，这些是未由上述任何 chunk 支撑的外部法律补充，不能保留为基于本书的答案。

**具体分析**：本次改提示词后，模型已经能识别“检索内容实际讲什么”和“用户具体所问”之间的差距，b010 因而保留为质量良好的无答案题。仍需后续从生成侧阻止它在明确披露之后追加未经检索验证的通用法律意见。

## chapter-06~09.pdf 章节（law-b011~018）与本批无答案题（law-b019~020，待用户审核）

chapter-06=41、chapter-07=35、chapter-08=36、chapter-09=41 个 chunk，本批原定题量槽位为 2/3/2/3。b011~b018 提供的章节事实覆盖为 2/3/2/1；按审核决定，b019、b020 替换原先 chapter-09 槽位中的两道错误事实题，重出为无答案诊断题。因此这两题计入本批的最后两个题量槽位，但不虚构 chapter-09 的支持来源或 supporting chunk。全部经`eval/audit_question.py --subject law`的真实`answer()`管线审查；同一题的重复运行若走出不同路径，均保留记录，不挑选较好的运行覆盖较差的运行。

### law-b011（匿名线索的被核实预测）

**题目**（ZH，事实题）：“匿名者寄信说一对夫妇会把装满毒品的车从佛州开回家乡；警方随后独立核实了信中关于航班、车辆所在地和返程计划的多项细节，但仍不知道匿名者是谁。法官能否把这些被核实的预测当作签发搜查令时支持 probable cause 的依据？”

**检索query**：`probable cause for search warrant based on anonymous tip with verified details`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-35.pdf/p0004/0008` | 0.3262 | 部分能（令状宣誓书的一般规则） |
| `chapter-06.pdf/p0007/0011` | 0.3357 | **能，GT，多数意见的未来预测核实规则** |
| `chapter-21.pdf/p0013/0023` | 0.3390 | 部分能（匿名线索的合理怀疑） |
| `chapter-21.pdf/p0017/0032` | 0.3411 | 不能（另一匿名线索案） |
| `chapter-21.pdf/p0016/0029` | 0.3495 | 不能（另一匿名线索案） |

**回答是否准确：准确。** 模型正确说明被独立核实的未来行动可为匿名线索其余内容提供可信基础；真实命中GT，保留。

### law-b012（交通拦停的隐藏动机）

**题目**（EN，事实题）："An officer sees me commit a real traffic violation and pulls me over, but his unspoken purpose is to look for evidence of drug crimes. Does that hidden motive by itself make the stop an unreasonable Fourth Amendment seizure?"

**前端检索记录**：前端会话保存的自动检索文本本身含有截断符，不能把它当作完整问题重印；以下完整 citation 和 score 来自该前端运行在生产`law`库中的记录。

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-21.pdf/p0018/0034` | 0.2718357444 | 部分能（交通拦停的客观合理怀疑标准） |
| `chapter-06.pdf/p0013/0022` | 0.2760425806 | **能，GT**：主观意图不属于普通probable-cause第四修正案分析 |
| `chapter-19.pdf/p0018/0034` | 0.2782050371 | 部分能（客观标准的一般论述） |
| `chapter-06.pdf/p0014/0024` | 0.2941614985 | 部分能（Whren案中对客观标准的讨论） |
| `chapter-10.pdf/p0013/0023` | 0.3038287759 | 部分能（搜查合理性的客观标准） |

**回答是否准确：准确，真实命中GT。** 用户前端多次运行稳定触发retrieve，且引用集包含核心多数意见chunk；以此前端实测为准。另一次隔离脚本的空历史复测曾走零次retrieve路径，只记录为跨运行上下文反复，不覆盖前端稳定结果。

### law-b013（申请书不能补救令状具体性缺陷）

**题目**（ZH，事实题）：“警察申请搜查令时，提交给法官的申请书详细列了要找的枪支和毒品；但实际交给我看的搜查令只写了笼统的“非法物品”，也没有引用或附上那份申请书。警察口头告诉我他们具体要找什么，能补救这张令状的缺陷吗？”

**检索query**（两轮）：`警察申请搜查令时需要向法官提交的材料要求，以及搜查令本身是否必须引用或附上申请书`；`搜查令中是否必须明确列出要寻找的具体物品，以及警察口头说明具体目标能否补救令状的模糊性`。

| 关键命中chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-07.pdf/p0008/0013` | 0.3378 | **能，GT**：令状须列明物品，或援引且随附申请书 |
| `chapter-08.pdf/p0008/0019` | 0.3463 | 部分能（具体性要求的一般表述） |
| `chapter-07.pdf/p0011/0018` | 0.3492 | 不能（异议意见） |

**回答是否准确：准确。** 两次检索后正确说明口头说明不能补救；原先一次日志未显示最终回答是审查命令的输出采集问题，不是管线没有返回。

### law-b014（no-knock的个案合理怀疑）

**题目**（EN，事实题）："Police have a warrant to search my motel room for drugs. When they arrive, I open the door, seem to recognize that they are police, and could quickly destroy the easily disposable drugs inside. May they force entry immediately without first knocking and announcing their authority?"

**检索query**：围绕“motel room warrant、drugs、occupant recognizes police、immediate forced entry、destruction of evidence”生成的英文查询。

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-07.pdf/p0018/0031` | 0.2790 | **能，GT/Top-1** |
| `chapter-07.pdf/p0016/0027` | 0.2887 | 能（否定毒品案的一概例外） |
| `chapter-07.pdf/p0017/0029` | 0.3194 | 部分能（案件事实） |

**回答是否准确：准确。** 正确适用“危险、徒劳或可能毁灭证据”的reasonable-suspicion标准。

### law-b015（knock-and-announce后的等待）

**题目**（ZH，事实题）：“警察持搜查令来到我家门口，先敲门并表明身份；屋内一片安静。若令状是为搜查可迅速冲入马桶销毁的毒品，他们只等了大约15到20秒就破门而入，这段等待一定不合理吗？”

**检索query**：`警察执行搜查令时，对于是否需要等待合理时间才能进入住宅的规定`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-07.pdf/p0019/0032` | 0.3221 | **能，GT/Top-1** |
| `chapter-08.pdf/p0007/0016` | 0.3300 | 不能 |
| `chapter-10.pdf/p0001/0001` | 0.3497 | 不能 |

**回答是否准确：准确。** 正确说明15–20秒在毒品、无回应等情境下可能合理，没有误写为固定时限。

### law-b016（现场住户能否仅因在场被搜身）——检索 miss 与原文伪造

**题目**（ZH，事实题）：“警方执行有效住宅搜查令时，我正住在被搜房屋内，但他们没有理由认为我本人涉案。能否仅凭我在现场就搜我的口袋和随身物品？”

**前端检索记录**：前端会话未保存工具调用 query；下表是该题前端实际返回的全部 citation 和 score。

| chunk | score | 实际内容与本题的关系 | 能否支撑答案 |
|---|---:|---|---|
| `chapter-10.pdf/p0002/0003` | 0.3427044153213501 | 逮捕后对被逮捕者及其立即控制范围的搜查 | 不能 |
| `chapter-09.pdf/p0010/0018` | 0.350297212600708 | plain feel 的触觉发现规则 | 不能 |
| `chapter-10.pdf/p0001/0001` | 0.35172271728515625 | search incident to lawful arrest 的概述 | 不能 |
| `chapter-11.pdf/p0017/0037` | 0.3565636873245239 | 同意搜查这一无令状例外 | 不能 |
| `chapter-10.pdf/p0005/0008` | 0.35808902978897095 | 关于逮捕、probable cause 和证据灭失的意见讨论 | 不能 |

**回答是否准确：结论本身正确，但没有检索支撑，且“原文节选”系伪造。** 正确规则位于`chapter-08.pdf/p0006/0014`（*Ybarra*），没有进入前端返回的五个 chunk。模型随后把上表内容虚构为“未涉案者没有一般搜查权”“逮捕后搜查是唯一例外”“仅凭在场不得搜人”等原文；逐字核对后，这些表述均不存在，且`chapter-11.pdf/p0017/0037`实际还在说明同意搜查这一不同例外。

**具体分析**：不能从“某一个例外不适用”反推“其他独立搜查依据均不存在”。本题保留为真实检索 miss 与来源忠实性缺陷，不改题。

### law-b017（已离开现场者的扣留）

**题目**（EN，事实题）：“I left my apartment shortly before police arrived to execute a search warrant there. Officers later find me away from the premises and detain me solely because I had been there earlier. Is that detention automatically covered by the authority to detain occupants during a warrant search?”

**检索query**：`legal authority to detain occupants during execution of a search warrant, and whether presence prior to search justifies detention`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-08.pdf/p0006/0015` | 0.2845 | 部分能 |
| `chapter-08.pdf/p0015/0031` | 0.2931 | 部分能 |
| `chapter-08.pdf/p0007/0016` | 0.2965 | **能，GT，排名第3** |

**回答是否准确：准确。** 正确给出Bailey的“immediate vicinity”限制。

### law-b018（plain view扣押）

**题目**（ZH，事实题）：“警察合法进入我家执行只准搜查失窃电视机的令状时，在客厅桌上看见一包明显是违禁品的毒品；令状没有写毒品。他们可以当场扣押这包毒品吗？”

**检索query**：`警察在执行搜查令时，发现未列明的违禁品是否可以当场扣押`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-09.pdf/p0009/0016` | 0.3526 | 不能（plain feel，而非plain view） |
| `chapter-08.pdf/p0007/0017` | 0.3756 | 不能 |
| `chapter-33.pdf/p0021/0035` | 0.3848 | 不能 |
| `chapter-20.pdf/p0011/0018` | 0.3855 | 不能 |
| `chapter-09.pdf/p0009/0017` | 0.3869 | **能**：明确复述plain-view的合法位置、违法性立即明显、可接触三项条件 |

**回答是否准确：准确，检索有支撑。** 原GT`chapter-09.pdf/p0005/0008`未命中，但`p0009/0017`本身足以由题面事实推出结论，已补入`supporting_chunks`。模型将plain view与Terry并列的表述不够严谨，但不改变本题结论和检索支撑。

### law-b019（加州自书遗嘱的有效性）——重出为无答案题

**题目**（ZH，无答案题）：“我母亲在加州去世前亲笔写了一份遗嘱，把房子留给我；这份遗嘱没有任何见证人签名。哥哥因此主张遗嘱无效。仅凭这些事实，我能否按该遗嘱继承房子？”

**检索query**：`加州遗嘱法对无见证人遗嘱的有效性规定`

| chunk | score | 能否推出该遗嘱是否有效 |
|---|---:|---|
| `chapter-11.pdf/p0001/0002` | 0.4850121736526489 | 不能（无令状同意搜查） |
| `chapter-39.pdf/p0017/0030` | 0.4948965311050415 | 不能（证人指认与排除规则） |
| `chapter-38.pdf/p0007/0012` | 0.49873489141464233 | 不能（刑事指认中的律师在场权） |
| `chapter-39.pdf/p0014/0025` | 0.5204961895942688 | 不能（照片指认程序） |
| `chapter-08.pdf/p0010/0022` | 0.5236007571220398 | 不能（住宅搜查令的特定性） |

**回答是否准确：检索边界披露正确，但后续补充越界。** 模型先明确说当前资料无法直接回答遗嘱有效性，这个判断完全正确；五个 chunk 都不能导出加州自书遗嘱、签名或见证人的规则。它随后却给出“自书遗嘱可能无见证有效”等通用法律说法和具体法条查询建议，未由检索内容支持。因此按“是否披露资料不足”的无答案题口径，不是无披露幻觉；按严格的仅依据检索作答标准，仍存在未获支持的法律补充。

**具体分析**：题目不是在问书是否覆盖遗嘱，而是在真实继承争议中直接提问；全库预检没有遗嘱、遗产认证或继承规则，真实 retrieve 也没有任何可用于推导结论的相邻依据。保留为有效的无答案诊断题。

### law-b020（受版权保护壁画的商业使用）——重出为无答案题

**题目**（EN，无答案题）：“I photographed a mural in a city park and want to print the photograph on T-shirts for sale. The mural is still under copyright, and I never asked the artist for permission. Is selling the shirts lawful?”

**检索query**：`copyright law and selling reproductions of copyrighted artwork without permission`

| chunk | score | 能否推出销售 T 恤是否合法 |
|---|---:|---|
| `chapter-14.pdf/p0022/0037` | 0.48918282985687256 | 不能（边境拘留与第四修正案） |
| `chapter-38.pdf/p0008/0014` | 0.49994802474975586 | 不能（笔迹样本与刑事诉讼权利） |
| `chapter-41.pdf/p0009/0015` | 0.504019558429718 | 不能（窃听法与刑事证据） |
| `chapter-41.pdf/p0002/0003` | 0.5150641202926636 | 不能（国家安全电子监控） |
| `chapter-32.pdf/p0007/0013` | 0.5160332322120667 | 不能（错误逮捕令与排除规则） |

**回答是否准确：准确拒答。** 模型明确指出这些结果不涉及版权或未经许可复制作品的合法性，并说不能根据当前材料判定，未把通用版权知识伪装成书中结论。

**具体分析**：这五个 chunk 没有一个包含版权、壁画、复制、合理使用或商品化规则；它们也不能通过类推得出答案。该题满足“确实不能由检索内容推出结论”的无答案题要求。

## chapter-06~09.pdf 批次小结（待用户审核）

| 题号 | 结果 |
|---|---|
| b011 | 准确，GT命中 |
| b012 | 准确，前端真实运行稳定命中GT；隔离空历史复测另有跳过检索反复 |
| b013 | 准确，GT命中 |
| b014 | 准确，GT Top-1 |
| b015 | 准确，GT Top-1 |
| b016 | 结论正确，但前端 Top-5 无支撑且后续伪造原文 |
| b017 | 准确，GT排名第3 |
| b018 | 准确，Top-5的`chapter-09.pdf/p0009/0017`可直接支撑 |
| b019 | 重出无答案题；五个 chunk 均不能推出结论，模型披露不足后仍有外部法律补充 |
| b020 | 重出无答案题；五个 chunk 均不能推出结论，模型准确拒答 |

## chapter-10~13.pdf 章节（law-b021~030，待用户审核，2026-07-24）

本批按四章 chunk 数比例分配 10 道事实题：chapter-10 2 道、chapter-11 3 道、chapter-12 3 道、chapter-13 2 道。以下为每题真实端到端 `retrieve` 的完整 Top-5，不以仅列出的引用替代分数表。

### law-b021（车辆逮捕附带搜查）

**题目**（EN，事实题）：“Police arrest me for driving with a suspended license. Before they search my car, I am handcuffed and locked in a patrol car, and they have no reason to think the passenger compartment contains evidence of that licensing offense. May they search the passenger compartment without a warrant as a search incident to my arrest?”

**检索 query**：`search incident to arrest and passenger compartment`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-10.pdf/p0010/0019` | 0.3577866554260254 | 部分能（车辆附带搜查规则背景） |
| `chapter-10.pdf/p0011/0020` | 0.38704073429107666 | 部分能（手铐、警车中的被捕者情境） |
| `chapter-10.pdf/p0010/0018` | 0.39215701818466187 | 能（即时控制范围与无法接触车辆） |
| `chapter-10.pdf/p0008/0014` | 0.4038569927215576 | 能（吊销驾照、已铐在警车、无证据性基础的 Gant 事实与结论） |
| `birchfield-v-north-dakota-2016.mp3/0027` | 0.4042079448699951 | 不能（酒驾呼气检测讨论） |

**回答是否准确：准确。** 模型正确给出“不可以”，并说明被捕者不能接触车辆且该罪名没有乘客舱证据基础。Top-5 中两段书本文本可直接支撑该结论；已把 qa 的依据更新为这两段，而不是保留未命中的旧 chunk。

### law-b022（逮捕后查看手机数据）

**题目**（ZH，事实题）：“警察合法逮捕我后扣下我的手机，确认手机本身没有武器风险；他们没有搜查令，也不存在其他紧急情况，只想翻看聊天记录和照片寻找犯罪证据。仅凭这次逮捕，他们能查看手机里的数字内容吗？”

**检索 query**：`警察在没有搜查令的情况下能否查看被逮捕者的手机中的数字内容`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-10.pdf/p0016/0029` | 0.3084104061126709 | 部分能（Riley 的背景） |
| `chapter-10.pdf/p0018/0032` | 0.3086177706718445 | 能（手机数字数据通常须令状，物理检查与数据不同） |
| `chapter-10.pdf/p0020/0035` | 0.3440418243408203 | 部分能（手机搜查的隐私理由） |
| `chapter-10.pdf/p0021/0038` | 0.3610299825668335 | 部分能（数字数据与传统随身物不同） |
| `chapter-10.pdf/p0001/0001` | 0.363842248916626 | 不能（一般第四修正案背景） |

**回答是否准确：准确。** 回答指出仅因逮捕不能翻阅数字内容、通常需要令状，并保留独立例外的条件；命中依据与标准答案一致。

### law-b023（未告知拒绝权的同意）

**题目**（ZH，事实题）：“警察因我车灯损坏把我拦下，没有逮捕我也没有搜查令，只问能否搜车；我回答“可以”。警察没有告诉我可以拒绝，但也没有威胁、强迫或暗示后果。仅因为他们没有告知拒绝权，这份同意就必然无效吗？”

**检索 query**：`在法律程序中，个人对警察搜查车辆的同意是否有效，如果警察未明确告知其有权拒绝`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-19.pdf/p0006/0010` | 0.327750563621521 | 部分能（同意搜查背景） |
| `chapter-15.pdf/p0012/0022` | 0.33452874422073364 | 部分能（自愿性背景） |
| `chapter-11.pdf/p0017/0037` | 0.33918607234954834 | 部分能（同意例外的一般规则） |
| `chapter-11.pdf/p0004/0007` | 0.3401182293891907 | 能（不知道可拒绝不是同意无效的必备条件） |
| `chapter-11.pdf/p0001/0001` | 0.3483468294143677 | 部分能（一般同意搜查规则） |

**回答是否准确：准确。** 模型的主结论是“不必然”，也说明总情境仍需判断。措辞中“没有胁迫使同意可能有效”略保守，但没有把它错误地写成充分条件；核心结论有原文直接支撑。

### law-b024（在场共同住户的明确反对）

**题目**（EN，事实题）：“Two co-tenants are both standing at the door when police ask to search their apartment without a warrant. One tenant says yes, but I expressly say no, and there is no emergency or other independent basis for entry. May police search based on the other tenant's consent?”

**检索 query**：`can police search an apartment without a warrant based on the consent of one co-tenant when the other co-tenant objects and there is no emergency or independent basis for entry`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-11.pdf/p0017/0037` | 0.29402482509613037 | 部分能（同意搜查的一般规则） |
| `chapter-11.pdf/p0011/0020` | 0.3042939305305481 | 部分能（共同住户同意背景） |
| `chapter-11.pdf/p0018/0038` | 0.31712353229522705 | 能（在场住户明确反对时，另一人的同意不足） |
| `chapter-11.pdf/p0015/0033` | 0.32182347774505615 | 部分能（相关案件讨论） |
| `chapter-08.pdf/p0010/0022` | 0.3256114721298218 | 不能（与共同住户同意无关） |

**回答是否准确：准确。** 模型把规则限定为“physically present objecting co-tenant”，并保留紧急情形等独立依据的例外，未扩大规则。

### law-b025（先前反对、后来共同住户同意）

**题目**（EN，事实题）：“Police lawfully arrest me outside the apartment I share with my partner after I expressly refuse consent to a search. About an hour later, while I am no longer present, my partner voluntarily consents to a search; there is no indication police removed me merely to avoid an objection. Does my earlier refusal itself bar that later consent search?”

**检索 query**：`whether a person's prior refusal to consent to a search can bar a subsequent voluntary consent by a cohabitant`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-11.pdf/p0011/0020` | 0.29418766498565674 | 部分能（共同住户同意背景） |
| `chapter-11.pdf/p0004/0007` | 0.3042528033256531 | 不能（个人同意的自愿性） |
| `chapter-11.pdf/p0018/0038` | 0.31727147102355957 | 能（Randolph 仅限同意时实际在场的反对者） |
| `chapter-11.pdf/p0015/0033` | 0.3194594383239746 | 部分能（相关案件讨论） |
| `chapter-11.pdf/p0014/0032` | 0.35267138481140137 | 部分能（共同住户同意背景） |

**回答是否准确：准确。** 模型正确说明先前反对本身不会永久阻却后来、在本人已合法离场后作出的自愿同意；题干也明确排除了“为规避反对而移走当事人”的关键争议。

### law-b026（热追捕进入住宅）

**题目**（ZH，事实题）：“警察有 probable cause 认为一名持枪抢劫重罪嫌疑人刚逃进一栋住宅，并且从街上一直连续追到门口。没有令状的情况下，他们能跟进住宅抓捕并为寻找嫌疑人和武器作必要查看吗？”

**检索 query**：`警察在没有搜查令的情况下，能否进入住宅逮捕持枪抢劫重罪嫌疑人并进行必要查看`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-10.pdf/p0002/0003` | 0.33133602142333984 | 部分能（一般紧急情形与搜查附带逮捕背景） |
| `chapter-12.pdf/p0002/0003` | 0.34000134468078613 | 能（持枪抢劫、连续追捕、无令状进入及必要查看） |
| `chapter-08.pdf/p0005/0010` | 0.34727537631988525 | 不能（街头扣留） |
| `chapter-10.pdf/p0005/0008` | 0.35220688581466675 | 不能（不同事实中的意见性讨论） |
| `chapter-15.pdf/p0016/0032` | 0.35369956493377686 | 部分能（入屋逮捕后的 protective sweep） |

**回答是否准确：核心结论准确，但理由有一处不精确。** 模型正确回答可在热追捕中进入，并命中与题干高度一致的 `chapter-12.pdf/p0002/0003`。但它把查看范围说成仅限“被捕者 immediate control”，混同了逮捕附带搜查；本题来源所支持的是为追捕嫌疑人、处理武器风险作合理必要查看。该瑕疵已记录，不把回答评成完全无误。

### law-b027（紧急救助进入住宅）

**题目**（ZH，事实题）：“警察接到住宅内激烈争吵的报告，到场后看见门外有血迹，透过窗户又看见屋内的人尖叫、砸东西。他们没有令状，但合理担心屋里可能有人受伤。可以为了确认是否需要紧急救助而进入吗？”

**检索 query**：`警察在没有令状的情况下，因合理担心屋内有人受伤，是否有权进入住宅进行紧急救助`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-12.pdf/p0010/0018` | 0.3050912618637085 | 能（尖叫或迫切危险迹象可支持无令状进入） |
| `chapter-12.pdf/p0015/0031` | 0.3353453278541565 | 能（血迹、尖叫、砸东西、需要立即援助的同案事实） |
| `chapter-12.pdf/p0022/0043` | 0.33971619606018066 | 部分能（紧急情形定义） |
| `chapter-12.pdf/p0014/0029` | 0.34741127490997314 | 能（不需要铁证；适用客观合理依据标准） |
| `chapter-15.pdf/p0016/0032` | 0.3485783338546753 | 不能（protective sweep，不是紧急救助） |

**回答是否准确：准确。** 结论、客观标准和“不要求铁证”均有直接文本支持，且题干事实与命中案例高度吻合。

### law-b028（无令状入户逮捕）

**题目**（EN，事实题）：“Police have probable cause to arrest me for a felony and believe I am inside my own home, but they have neither an arrest warrant nor a search warrant. There is no emergency. May they cross the threshold and arrest me inside?”

**检索 query**：`can police arrest someone inside their own home without a warrant when there is probable cause for felony`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-13.pdf/p0020/0034` | 0.31771421432495117 | 能（Payton：无紧急情形不得无令状在家中逮捕重罪嫌疑人） |
| `chapter-12.pdf/p0009/0015` | 0.32167887687683105 | 不能（该段为不同立场的政策性讨论） |
| `chapter-12.pdf/p0006/0011` | 0.33095991611480713 | 能（有逮捕令时才附带有限入户权限，反面支持本题） |
| `chapter-15.pdf/p0016/0032` | 0.3501773476600647 | 部分能（有逮捕令的入户规则） |
| `chapter-10.pdf/p0005/0008` | 0.3547210097312927 | 不能（不同案件事实） |

**回答是否准确：准确。** 模型没有把 probable cause 单独当作入户授权；“必须有令状或紧急情形”的结论由 Top-1 直接支持。末尾建议咨询律师属于泛化建议，不是用于支撑法律结论的外部规则。

### law-b029（酒精自然代谢是否当然紧急）

**题目**（ZH，事实题）：“我因涉嫌酒驾被逮捕后拒绝呼气检测。现场没有事故、伤者或其他特殊延误，警察也能迅速联系法官取得令状；他们只因为酒精会自然代谢，就强制抽血且不申请令状。酒精自然代谢这一点本身是否总能构成紧急情形？”

**检索 query**：`在酒驾案件中，警察因酒精自然代谢而无需申请搜查令直接抽血的法律依据`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-13.pdf/p0002/0004` | 0.3193144202232361 | 能（无特殊紧急情形、酒精代谢本身不足的 McNeely 事实） |
| `chapter-13.pdf/p0007/0012` | 0.3296448588371277 | 能（拒绝把酒精代谢视为当然紧急情形） |
| `chapter-13.pdf/p0006/0010` | 0.33505570888519287 | 能（能联系法官、未尝试令状的具体事实） |
| `chapter-13.pdf/p0007/0013` | 0.3359185457229614 | 部分能（不同意见，但也说明有时间须取令状） |
| `chapter-13.pdf/p0001/0003` | 0.344798743724823 | 能（必须按个案全部情境判断） |

**回答是否准确：准确。** 模型明确否定“当然紧急”，以个案整体情境为标准，并把题干中的可迅速取得令状作为不支持紧急性的事实；未夸大为“所有无令状抽血都非法”。

### law-b030（酒驾逮捕后的呼气检测与抽血）

**题目**（EN，事实题）：“After a lawful DUI arrest, officers have no warrant and no case-specific emergency. May they administer a breath test as a search incident to arrest? What if they instead require a blood draw?”

**检索 query**：`after a lawful DUI arrest, may officers administer a breath test as a search incident to arrest without a warrant and without case-specific emergency`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-13.pdf/p0011/0020` | 0.2831767797470093 | 部分能（呼气、抽血都是搜查及例外框架） |
| `chapter-13.pdf/p0017/0029` | 0.30362528562545776 | 部分能（附带逮捕搜查的讨论） |
| `birchfield-v-north-dakota-2016.mp3/0016` | 0.30613958835601807 | 不能（当事人一方的口头主张，非判决规则） |
| `chapter-13.pdf/p0014/0025` | 0.3130320906639099 | 能（breath test 可作为逮捕附带搜查的理由） |
| `chapter-13.pdf/p0002/0004` | 0.31307411193847656 | 部分能（无紧急情形下抽血的 McNeely 事实） |

**回答是否准确：准确。** 回答把呼气检测和抽血分开：前者通常可作为逮捕附带搜查，后者不能仅凭该理由进行，通常需要令状或独立例外。它没有把酒精自然代谢写成自动例外。

## chapter-10~13.pdf 批次小结（待用户审核）

| 题号 | 结果 |
|---|---|
| b021 | 准确；两个直接支撑 chunk 在 Top-5 |
| b022 | 准确；GT 在 Top-2 |
| b023 | 准确；核心规则在 Top-4 |
| b024 | 准确；核心规则在 Top-3 |
| b025 | 准确；核心规则在 Top-3 |
| b026 | 结论与命中依据正确；范围理由混同 doctrinal test，需作为轻微生成错误记录 |
| b027 | 准确；多个 Top-5 chunk 直接命中题干事实与规则 |
| b028 | 准确；Payton 规则 Top-1 |
| b029 | 准确；个案判断和可取得令状的事实均命中 |
| b030 | 准确；呼气/抽血区分获得直接或相邻文本支持 |

## chapter-14~17.pdf 章节与无答案题（law-b031~042，待用户审核，2026-07-24）

本批按实际 chunk 数分配 10 道事实题：chapter-14（45）为 3 道、chapter-15（39）为 2 道、chapter-16（40）为 2 道、chapter-17（47）为 3 道；另加入并验证 2 道无答案题。以下均为真实端到端 `retrieve` 的完整 Top-5。

### law-b031（边境油箱搜查）

**题目**（EN，事实题）：“I drive from Mexico into the United States through an official port of entry. A customs officer, without any warrant, probable cause, or particular suspicion, wants to open my car's fuel tank to look for contraband. Is that routine border search unreasonable under the Fourth Amendment simply because the officer has no individualized suspicion?”

**检索 query**：`Fourth Amendment and routine border searches including inspection of vehicle fuel tanks without individualized suspicion`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-14.pdf/p0002/0003` | 0.28595423698425293 | 能（油箱拆检与无需怀疑的争点） |
| `chapter-14.pdf/p0003/0005` | 0.2864863872528076 | 部分能（油箱拆检的侵入性） |
| `chapter-14.pdf/p0013/0021` | 0.289048969745636 | 能（边境进入本身使搜查合理，无需 probable cause） |
| `chapter-14.pdf/p0008/0014` | 0.2950315475463867 | 不能（固定检查站的范围） |
| `chapter-14.pdf/p0017/0027` | 0.2994840741157532 | 能（边境例行搜查无需合理怀疑、probable cause 或令状） |

**回答是否准确：准确。** 结论与题干中“官方入境口岸、燃油箱、无个别怀疑”均有直接或组合支持。回答增加的具体下级法院案名未由当前 chunk 明示，不作为结论依据；核心规则未受影响。

### law-b032（固定移民检查站）

**题目**（EN，事实题）：“Border Patrol officers stop every car for a brief immigration question at a fixed, clearly marked checkpoint on a highway away from the physical border. They select no drivers individually and have no particular suspicion about me. Is the stop automatically unconstitutional merely because they lack individualized suspicion?”

**检索 query**：`constitutional requirements for traffic stops at immigration checkpoints without individualized suspicion`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-15.pdf/p0012/0021` | 0.3238677978515625 | 部分能（无个别怀疑并不必然决定合宪性） |
| `chapter-14.pdf/p0008/0014` | 0.3428117036819458 | 能（固定检查站简短询问合宪，进一步拘留/搜查另需依据） |
| `chapter-15.pdf/p0013/0025` | 0.3692284822463989 | 部分能（信息征集型检查点） |
| `chapter-14.pdf/p0007/0011` | 0.3718447685241699 | 能（短暂询问、低侵入性与固定检查站理由） |
| `chapter-14.pdf/p0006/0010` | 0.3720964789390564 | 部分能（roving patrol 需要合理怀疑的对照） |

**回答是否准确：准确。** 模型没有把固定检查站误写成可任意搜车，明确限于简短问询与最小侵入；这与命中原文一致。

### law-b033（体内藏毒的边境扣留）

**题目**（EN，事实题）：“At the border, customs officers think I may have swallowed drug-filled balloons. They rely on a particularized set of facts and trained inferences, not merely a hunch, but they do not yet have probable cause. May they detain me for this suspected alimentary-canal smuggling, or is probable cause always required first?”

**检索 query**：`probable cause requirement for detaining someone suspected of alimentary-canal smuggling at the border`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-14.pdf/p0018/0028` | 0.28713691234588623 | 能（particularized/objective reasonable suspicion 足够） |
| `chapter-14.pdf/p0019/0030` | 0.32292211055755615 | 部分能（扣留时长的合理性） |
| `chapter-14.pdf/p0016/0026` | 0.37392526865005493 | 部分能（继续观察的事实背景） |
| `chapter-14.pdf/p0013/0021` | 0.40825557708740234 | 部分能（边境搜查一般规则） |
| `chapter-14.pdf/p0017/0027` | 0.4151189923286438 | 部分能（边境例外背景） |

**回答是否准确：准确。** 回答正确区分了初始 reasonable suspicion 与扣留范围/时长仍须合理的要求，没有把它扩大为可无限期或任意侵入。

### law-b034（以缉毒为主要目的的检查站）

**题目**（EN，事实题）：“A city sets up a highway roadblock where officers briefly stop predetermined cars, check licenses, and use drug-sniffing dogs. The program's stated primary purpose is finding ordinary illegal-drug offenses, not responding to an immediate road-safety threat. May the city run it without individualized suspicion?”

**检索 query**：`whether a city may operate a highway roadblock for drug detection without individualized suspicion`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-15.pdf/p0010/0016` | 0.3770284652709961 | 不能（反对意见的不同立场） |
| `chapter-15.pdf/p0009/0015` | 0.3979523181915283 | 不能（反对意见） |
| `chapter-15.pdf/p0014/0026` | 0.4034731984138489 | 能（教材明确说明不得为查毒而设检查站） |
| `chapter-15.pdf/p0007/0011` | 0.413119375705719 | 能（主要目的为一般犯罪侦查即违反第四修正案） |
| `chapter-15.pdf/p0008/0012` | 0.41385501623153687 | 能（缉毒不能伪装成即时道路安全威胁） |

**回答是否准确：准确。** 模型正确识别“主要目的”这一限定；虽 Top-1 和 Top-2 是反对意见，但后三段直接给出多数规则，足以支撑结论。

### law-b035（protective sweep 的两层范围）

**题目**（EN，事实题）：“Police lawfully arrest someone inside a house. Without probable cause or reasonable suspicion that anyone else is dangerous, may they quickly look in the closets and rooms immediately adjoining the arrest location from which an attack could be launched? May they then sweep every other room in the house on the same basis?”

**检索 query**：`police search of a residence after lawful arrest, including searching closets and adjacent rooms for potential attacks, and whether this extends to sweeping every other room`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-15.pdf/p0019/0037` | 0.28174370527267456 | 部分能（sweep 只能是可藏人的粗略检查） |
| `chapter-15.pdf/p0016/0032` | 0.3092907667160034 | 能（相邻区域无需另加怀疑；更远区域须 articulable facts） |
| `chapter-12.pdf/p0010/0017` | 0.32482630014419556 | 不能（教材提问） |
| `chapter-15.pdf/p0017/0033` | 0.32669806480407715 | 能（非自动、非全屋；范围和时长限制） |
| `chapter-15.pdf/p0014/0028` | 0.33239245414733887 | 部分能（protective sweep 概述） |

**回答是否准确：准确。** 两问分别回答，并准确保留“相邻处的例外”与“超出后须有可陈述事实”的差别。

### law-b036（学校官员搜书包）

**题目**（EN，事实题）：“A public-school assistant principal has reasonable grounds to think a student violated a school rule. Before looking in the student's backpack, must the principal first obtain a warrant and establish probable cause in the same way police ordinarily would?”

**检索 query**：`school officials' authority to search students' belongings without a warrant and whether they need probable cause like police`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-16.pdf/p0005/0008` | 0.2539774179458618 | 能（学校搜查无需令状，标准低于 probable cause） |
| `chapter-16.pdf/p0005/0009` | 0.28318899869918823 | 能（起始和范围均须合理） |
| `chapter-11.pdf/p0009/0016` | 0.30801165103912354 | 不能（教材假设题） |
| `chapter-11.pdf/p0001/0001` | 0.31579554080963135 | 不能（同意搜查） |
| `chapter-09.pdf/p0001/0000` | 0.3171364665031433 | 不能（一般令状例外背景） |

**回答是否准确：准确。** 模型正确回答“无须令状或 probable cause”，同时没有遗漏搜查仍须按起始依据和范围接受合理性审查。

### law-b037（学生 strip search）

**题目**（EN，事实题）：“A school official has some reason to suspect a middle-school student possessed ordinary ibuprofen pills, but no information suggests the pills are dangerous, that the student still has them, or that she hid them in her underwear. May the official require a strip search down to the student's underwear merely because students sometimes hide contraband under clothing?”

**检索 query**：`whether school officials may require a strip search of a student based on suspicion of contraband hidden under clothing, without evidence of danger or possession`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-16.pdf/p0013/0024` | 0.317274808883667 | 能（普通止痛药、无内衣藏匿迹象不足） |
| `chapter-18.pdf/p0007/0012` | 0.32060402631759644 | 部分能（strip search 的高度侵入性） |
| `chapter-17.pdf/p0014/0027` | 0.35697293281555176 | 不能（学生运动员普遍检测） |
| `chapter-09.pdf/p0009/0016` | 0.3614845275878906 | 不能（plain feel） |
| `chapter-16.pdf/p0010/0019` | 0.36208170652389526 | 部分能（学校搜索的合理性框架） |

**回答是否准确：准确。** 核心结论和三项关键事实（药物不危险、无现有持有迹象、无内衣藏匿依据）均来自 Top-1。

### law-b038（铁路安全岗位药检）

**题目**（EN，事实题）：“After a serious railroad accident, a federal safety rule requires breath and urine testing of crew members in safety-sensitive jobs even though supervisors have no individualized suspicion that a particular worker used drugs or alcohol. Does the lack of individualized suspicion alone make the testing unconstitutional?”

**检索 query**：`federal safety rule requiring breath and urine testing of railroad crew members in safety-sensitive jobs without individualized suspicion, constitutionality`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-17.pdf/p0001/0002` | 0.333248496055603 | 部分能（事故后测试规则） |
| `chapter-17.pdf/p0007/0010` | 0.3694573640823364 | 能（无令状、无合理怀疑仍属合理） |
| `chapter-17.pdf/p0002/0004` | 0.37699973583221436 | 部分能（Subpart D 的触发条件） |
| `chapter-17.pdf/p0003/0005` | 0.3921523094177246 | 能（special-needs 平衡框架） |
| `chapter-17.pdf/p0005/0007` | 0.4186052083969116 | 部分能（测试侵入性） |

**回答是否准确：准确。** 回答没有把所有工作场所测试泛化为合宪，而是限于铁路安全岗位、触发事件和本书的 special-needs 平衡。

### law-b039（课外活动学生药检）

**题目**（EN，事实题）：“A public school requires students who voluntarily join competitive extracurricular activities to provide a urine sample for a suspicionless drug-testing program. The school has no individualized reason to suspect me. Is the program necessarily unconstitutional for that reason alone?”

**检索 query**：`constitutional requirements for drug testing in public schools without individualized suspicion`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-17.pdf/p0014/0027` | 0.3632204532623291 | 部分能（Vernonia 的普遍检测理由） |
| `chapter-17.pdf/p0013/0025` | 0.3900870084762573 | 部分能（学校 guardian/tutor special need） |
| `chapter-17.pdf/p0019/0040` | 0.3977851867675781 | 不能（医院向警方提供检测结果） |
| `chapter-17.pdf/p0015/0031` | 0.4088069200515747 | 部分能（并非所有学生的普遍检测都当然合宪） |
| `chapter-17.pdf/p0015/0028` | 0.41073787212371826 | 能（Earls：competitive extracurricular activities 的具体规则） |

**回答是否准确：核心结论准确，但有案例名错误。** “无个别怀疑不必然违宪”及其条件有书内直接支持。模型却把案例写成 “Earls v. Virginia”；这不是书中案例的正确名称，属于不必要且错误的外部化引注，已记录为生成质量问题。

### law-b040（医院向警方提供孕妇尿检结果）

**题目**（EN，事实题）：“A state hospital secretly tests pregnant patients' urine for cocaine, then turns positive results over to police so that patients can be investigated or prosecuted. The hospital has neither probable cause nor informed consent. Can it justify this program as a suspicionless special-needs search merely by saying it wants to protect health?”

**检索 query**：`suspicionless special-needs search in the context of pregnant patients and drug testing`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-17.pdf/p0017/0037` | 0.34452593326568604 | 能（以执法取证为目的的非同意诊断测试） |
| `chapter-17.pdf/p0019/0040` | 0.3705064654350281 | 能（州医院、尿检是搜查、special needs 的门槛） |
| `chapter-17.pdf/p0013/0025` | 0.38370227813720703 | 部分能（学校药检的不同 special-needs 环境） |
| `chapter-17.pdf/p0020/0041` | 0.3840717077255249 | 能（向非医疗人员披露结果的隐私侵害） |
| `chapter-17.pdf/p0020/0042` | 0.38993775844573975 | 能（即时主要目的为执法取证） |

**回答是否准确：准确。** 它准确把“最终希望治疗”与“即时主要目的为执法取证”区分开来，未接受单纯的健康表述作为 special-needs 掩护。

### law-b041（芝加哥租赁押金）——无答案题

**题目**（EN，无答案题）：“I rented an apartment in Chicago, paid a $2,000 security deposit, and moved out after leaving the unit undamaged. My landlord kept the entire deposit for 45 days without giving me an itemized statement. Under the applicable landlord-tenant law, am I entitled to get the deposit back or recover a penalty?”

**检索 query**：`landlord-tenant law in Chicago regarding return of security deposit and time limits for providing itemized statements`

| chunk | score | 能否推出押金返还或罚金 |
|---|---:|---|
| `chapter-11.pdf/p0013/0029` | 0.486056387424469 | 不能（共同住户同意搜查） |
| `carpenter-v-united-states-2017.mp3/0002` | 0.4967060685157776 | 不能（基站定位隐私） |
| `carpenter-v-united-states-2017.mp3/0011` | 0.4976658225059509 | 不能（位置数据与隐私政策） |
| `chapter-27.pdf/p0020/0037` | 0.5017109513282776 | 不能（Miranda/Edwards） |
| `chapter-11.pdf/p0019/0040` | 0.5023422837257385 | 不能（同住人反对搜查的时效） |

**回答是否准确：准确拒答。** 模型明确说明检索内容没有芝加哥租赁、押金、清单或罚金规则，无法依据本书判断；没有用训练知识给出法定时限或结论。五个 chunk 均不能通过类推推出该问题的答案。

### law-b042（孕期就业歧视）——无答案题

**题目**（EN，无答案题）：“I told my private employer that I was pregnant, and one week later it fired me. The employer says my position was eliminated but hired another person to perform substantially the same work. Based on these facts, do I have a federal employment-discrimination claim?”

**检索 query**：`federal employment discrimination claim based on pregnancy and termination`

| chunk | score | 能否推出联邦就业歧视请求 |
|---|---:|---|
| `chapter-36.pdf/p0013/0021` | 0.5139328837394714 | 不能（刑事辩护无效与利益冲突） |
| `chapter-23.pdf/p0014/0023` | 0.525323748588562 | 不能（无相关实体规则） |
| `chapter-17.pdf/p0019/0039` | 0.5266885161399841 | 不能（孕妇尿检与逮捕政策） |
| `chapter-32.pdf/p0015/0028` | 0.5273706912994385 | 不能（排除规则与先例） |
| `chapter-35.pdf/p0001/0002` | 0.5330653190612793 | 不能（刑事程序引注） |

**回答是否准确：准确拒答。** 模型明确披露：当前资料没有孕期就业、Title VII 或 Pregnancy Discrimination Act 的规则，不能下确定结论。它只把这些法律作为“需要检索到的材料”举例，并未据此作答；本书的孕妇尿检内容也完全不能支持就业歧视结论。

## chapter-14~17.pdf 批次小结（待用户审核）

| 题号 | 结果 |
|---|---|
| b031 | 准确；边境油箱与一般边境规则均命中 |
| b032 | 准确；固定检查站的简短问询规则命中 |
| b033 | 准确；reasonable suspicion 规则 Top-1 |
| b034 | 准确；关键多数规则排名第3至5，Top-1/2 是反对意见 |
| b035 | 准确；相邻区域与非相邻区域的不同门槛均命中 |
| b036 | 准确；两项核心文本排名第1、2 |
| b037 | 准确；题干事实与 Top-1 高度一致 |
| b038 | 准确；铁路安全岗位的无个别怀疑规则排名第2 |
| b039 | 核心结论准确；错误写作 “Earls v. Virginia” 已记录 |
| b040 | 准确；执法取证目的与 special-needs 限制均命中 |
| b041 | 有效无答案题；五个结果全部无关，模型准确披露不足 |
| b042 | 有效无答案题；五个结果全部无关，模型准确披露不足 |

## law-b043：入监前 visual strip search 的真实检索缺陷（2026-07-24）

该题保留为有效事实题和检索质量缺陷样本，不因本轮模型回答矛盾而删除。它与已发现的 law-b002 一类情况相同：语料中存在支持标准答案的多数规则，但真实 `retrieve` 没有把该依据送进 Top-5，反而集中命中反对意见和相邻材料。

**题目**（EN，事实题）：“I am arrested for a minor offense and will be placed into a jail's general population. The jail has a policy requiring a visual strip search of every incoming detainee, even without individualized suspicion that I carry contraband. Is the policy automatically unreasonable merely because my charge is minor and officers lack particular suspicion?”

**标准答案**：进入一般监区的被拘留者可以适用合理的入监搜查政策；轻罪和没有个别怀疑本身不自动使政策不合理。监狱安全和违禁品控制具有重要权重。本书的 `chapter-18.pdf/p0002/0004` 包含多数规则。

**检索 query**：`policy requiring visual strip search of every incoming detainee without individualized suspicion`

| chunk | score | 能否支撑标准答案 |
|---|---:|---|
| `chapter-17.pdf/p0014/0027` | 0.4316837787628174 | 不能（学生运动员普遍药检的讨论） |
| `chapter-18.pdf/p0007/0012` | 0.433762788772583 | 不能（反对 suspicionless strip search 的异议论证） |
| `chapter-18.pdf/p0005/0010` | 0.43509143590927124 | 不能（明确为反对多数结论的 dissent） |
| `chapter-18.pdf/p0007/0013` | 0.4372867941856384 | 不能（异议结论） |
| `chapter-18.pdf/p0006/0011` | 0.440426766872406 | 不能（异议中的理由） |

**回答是否准确：不准确且自相矛盾。** 模型开头正确说“并非自动不合理”，但随后把 Top-5 的反对意见当作规则，称该政策“可能违宪且须 reasonable suspicion”，最后又重复“并非自动不合理”。它没有检索到多数结论所在的 `chapter-18.pdf/p0002/0004`，因此不能把相反的异议材料推成标准答案。

**缺陷判定**：真实检索缺陷，而不是无答案题或题干缺陷。正确依据在同一章、与题面高度对应，但未进入 Top-5；Top-5 又形成单侧的反对意见污染，使生成答案发生内部冲突。该题应保留，用于后续检索改进的回归测试。

## law-b048、b055、b056：本批待审问题（2026-07-24）

以下为真实端到端审查中发现的问题。题目均先保留在 `qa.jsonl`，不自行删除或改变结论，等待用户统一审查。

### law-b048（交通拦截延长后进行狗嗅探）——检索错位

**题目**（EN，事实题）：“During a lawful traffic stop, an officer finishes the tasks tied to the traffic violation, returns my documents, and then keeps me for several additional minutes solely to walk a drug-sniffing dog around my car. The officer has no reasonable suspicion of other crime. Is the extra detention lawful because a dog sniff itself is not a Fourth Amendment search?”

**检索 query**：`Fourth Amendment and vehicle searches involving drug-sniffing dogs`

| chunk | score | 能否支撑“不得无依据延长既已完成的拦截” |
|---|---:|---|
| `chapter-05.pdf/p0017/0029` | 0.274380087852478 | 不能（住宅门廊 dog sniff） |
| `chapter-05.pdf/p0016/0026` | 0.2876065969467163 | 不能（对 dog sniff 是否为搜查的不同观点） |
| `chapter-05.pdf/p0012/0019` | 0.28825443983078003 | 部分能（机场行李 dog sniff 不是搜查，但不是交通拦截延长） |
| `chapter-05.pdf/p0016/0028` | 0.2937459945678711 | 不能（异议性 dog sniff 讨论） |
| `chapter-05.pdf/p0015/0025` | 0.29405784606933594 | 不能（dog sniff 理论讨论） |

**回答是否准确：核心结论正确，但不受本轮检索支撑。** 模型正确回答不得在没有独立 reasonable suspicion 时延长拦截，但 Top-5 没有 `chapter-20.pdf` 中的 Rodriguez 文本；回答混入错误的 `United States v. Place (2004)` 年份/归属和相互冲突的 dog-sniff 表述。该题应保留为“GT 在书内、真实 retrieve 错位、模型借训练知识得出正确结论”的回归样本。

### law-b055（加州用餐休息工资）——真实前端准确披露不足

**题目**（EN，无答案题）：“I am a nonexempt employee in California. My employer schedules me for a six-hour shift but provides no meal break and pays no additional amount. Under the applicable California wage-and-hour law, am I owed a meal-period premium?”

**真实前端检索结果**：已核对 2026-07-24 15:24 保存的三次前端端到端对话；三次回答和五个引用一致。前端结果没有发生重复 retrieve，也没有 `MAX_ROUNDS_EXCEEDED`。

| chunk | score | 能否推出加州用餐休息或 premium |
|---|---:|---|
| `chapter-18.pdf/p0017/0034` | 0.5478039979934692 | 不能（DNA 收集与身份识别） |
| `chapter-10.pdf/p0001/0000` | 0.5568079948425293 | 不能（逮捕附带搜查章节标题） |
| `chapter-11.pdf/p0001/0000` | 0.5577885508537292 | 不能（同意搜查章节标题） |
| `chapter-31.pdf/p0008/0013` | 0.5606318116188049 | 不能（排除规则适用于州的讨论） |
| `chapter-15.pdf/p0001/0000` | 0.5653861165046692 | 不能（令状例外章节标题） |

**回答是否准确：准确拒答。** 三次真实前端回答均明确说明：“检索结果不包含与 California wage-and-hour、meal breaks 或 meal-period premiums 有关的信息”，因此“cannot determine whether you are owed a meal-period premium ... based on this information”。它只建议查阅官方加州劳动法规或咨询专业人士，没有把外部加州工资法伪装成本书结论。

**审查环境说明**：隔离的 `audit_question.py` 曾对同题发生反复改写 query 并达到 `[MAX_ROUNDS_EXCEEDED]`；这与用户真实前端的三次稳定披露不一致。按既定原则，以真实前端端到端结果为准：不将该隔离环境异常记为 b055 的模型缺陷。该异常如需处理，应另作为审查工具/服务状态差异排查，不能覆盖本题结论。

### law-b056（数字音乐下载与 first-sale doctrine）——未披露的外部法律补全

**题目**（EN，无答案题）：“I bought a song download from an online music store and then copied the file onto 500 USB drives to sell at a concert. The store's terms did not expressly grant resale rights. Does the first-sale doctrine make those sales lawful?”

**检索 query**：`first-sale doctrine and its application to digital music downloads`

| chunk | score | 能否推出数字音乐复制销售是否受 first-sale doctrine 保护 |
|---|---:|---|
| `carpenter-v-united-states-2017.mp3/0060` | 0.49291038513183594 | 不能（第四修正案 subpoena 论证） |
| `chapter-05.pdf/p0006/0008` | 0.5098965167999268 | 不能（CSLI 与第三方原则） |
| `chapter-03.pdf/p0024/0038` | 0.5155367851257324 | 不能（第三方披露理论的教材提问） |
| `chapter-02.pdf/p0012/0021` | 0.5171360373497009 | 不能（数字时代的隐私理论） |
| `carpenter-v-united-states-2017.mp3/0037` | 0.5211843848228455 | 不能（位置数据的 property-right 假设） |

**回答是否准确：不受检索支撑的确定性作答。** 模型断言 first-sale doctrine 不适用于数字下载、购买者通常只取得 licence、复制到 500 个 USB 一定侵犯复制与发行权；这些均不是任何命中 chunk 的内容，回答也没有先披露资料不足。因此该题保留为有效无答案题和高风险法律幻觉回归样本。

## chapter-22~25.pdf 批次（b057~b066，2026-07-24，待用户审核）

本批按各章 chunk 量分配为第 22 章 2 题、第 23 章 3 题、第 24 章 2 题、第 25 章 3 题。为修正全套语言比例，b058~b066 已改为中文；b057 保留英文。每题都以真实 `book_id=law-eval` 的端到端审查为依据；下表完整列出该次调用的 Top-5 分数（b062 的回答阶段未返回，分数由其已实际发出的同一 retrieve query 直接复核）。

### law-b057（36 小时接力讯问）

**题目**（EN，事实题）：“Police question me in relays for about 36 hours, allowing virtually no rest, until I confess. Even if no officer physically strikes me, may the confession be treated as voluntary simply because I eventually answered questions?”

**检索 query**：`legal standards for voluntariness of confession during prolonged police interrogation including lack of sleep and rest`

| chunk | score | 能否直接支撑“不自愿” |
|---|---:|---|
| `chapter-22.pdf/p0007/0011` | 0.39149874448776245 | 能（精神强迫亦可压倒意志） |
| `chapter-22.pdf/p0020/0034` | 0.3964877128601074 | 部分能（Connelly 的警察强制前提） |
| `chapter-22.pdf/p0021/0035` | 0.4008190631866455 | 能（总情境判断及警察行为要求） |
| `chapter-22.pdf/p0019/0032` | 0.40139174461364746 | 能（无与供述有因果关系的警察行为则无正当程序违反） |
| `chapter-22.pdf/p0015/0026` | 0.4038197994232178 | 能（供述须为自由且不受约束的选择） |

**回答是否准确：准确。** 以真实前端本次结果为准。它没有命中更贴近事实的 Ashcraft 段落，但无需把“同一事实逐字复现”当作唯一可作答路径：Top-1 的精神强迫、Top-3 的总情境判断和 Top-5 的自由选择标准能够共同推出“36 小时接力、几乎无休息的供述不能仅因最终回答就被视为自愿”。题干本身已给定长期与无休息这两个关键情境。此题不是未召回或检索缺陷。

### law-b058（以暴民伤害威胁取得供述）

**题目**（ZH，事实题）：“我被羁押时，一名警察告诉我外面有愤怒的人群想伤害我，并暗示只有认罪才能得到保护；随后我作了供述。国家能否仅因威胁是通过言语而非实际肢体暴力传达，就把这份供述当作自愿供述使用？”

**检索 query**：`在羁押期间，警察以言语威胁（如暗示只有认罪才能得到保护）是否构成强迫或非自愿供述，以及国家能否据此将该供述作为合法证据使用的法律标准`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-23.pdf/p0009/0013` | 0.30689293146133423 | 部分能（威胁、欺骗或诱导会破坏自愿放弃） |
| `chapter-23.pdf/p0010/0014` | 0.3273662328720093 | 部分能（无强制影响的供述才可采） |
| `chapter-25.pdf/p0010/0015` | 0.34148287773132324 | 不能（卧底狱友情境） |
| `chapter-34.pdf/p0010/0014` | 0.3435312509536743 | 部分能（强制策略破坏意志） |
| `chapter-23.pdf/p0008/0012` | 0.35079002380371094 | 部分能（律师与讯问的 Miranda 规则） |

**回答是否准确：准确。** Top-1/2 对威胁、诱导和强制影响的规则，结合题干中明确的暴民伤害与“认罪才能受保护”的警察暗示，足以推导标准答案。不得把未返回完全相同的暴民事实段落标成“未召回”。

### law-b059（精神疾病者主动供述）

**题目**（ZH，事实题）：“一名有严重精神疾病的人主动走向警察并供认犯罪；警察没有讯问、威胁、许诺或以其他方式强迫他。仅因这份供述可能不可靠，正当程序条款本身是否要求排除该供述？”

**检索 query**：`Due Process Clause and suppression of confessions based on unreliability without coercion`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-23.pdf/p0011/0016` | 0.3380119800567627 | 不能（Miranda 异议背景） |
| `chapter-22.pdf/p0019/0033` | 0.35504859685897827 | 能（警察强制活动是必要前提） |
| `chapter-01.pdf/p0003/0004` | 0.35782772302627563 | 不能（历史案件程序） |
| `chapter-22.pdf/p0019/0032` | 0.36066877841949463 | 能（无与供述有因果关系的警察行为即无正当程序剥夺） |
| `chapter-22.pdf/p0014/0024` | 0.3608710765838623 | 不能（反对意见） |

**回答是否准确：准确。** 模型明确以 coercive police activity 为必要前提，并正确说明精神疾病本身不完成正当程序违反；两段直接多数规则均已命中。

### law-b060（遗漏关键 Miranda 告知）

**题目**（ZH，事实题）：“在羁押讯问前，警察只告诉我‘你可以保持沉默’，却没有告知我的陈述可以被用来对付我，也没有告知我可以咨询律师；随后我回答了问题。这种不完整的告知足以证明我有效放弃了 Miranda 权利吗？”

**检索 query**：`Miranda waiver requirements and what constitutes a valid warning under the Fifth Amendment`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-34.pdf/p0008/0011` | 0.30062127113342285 | 部分能（无告知陈述的排除后果） |
| `chapter-34.pdf/p0007/0010` | 0.32273292541503906 | 部分能（未告知陈述推定受强迫） |
| `chapter-25.pdf/p0019/0031` | 0.334256649017334 | 能（须充分告知、包括陈述可被用作证据） |
| `chapter-26.pdf/p0005/0007` | 0.33603549003601074 | 部分能（知情自愿放弃） |
| `chapter-26.pdf/p0003/0005` | 0.33907073736190796 | 部分能（完整告知与书面放弃） |

**回答是否准确：准确。** 尽管题目所标 chapter 23 页未排入 Top-5，Top-3 明确支撑“只说可沉默而遗漏陈述后果/律师”不足以构成知情放弃。

### law-b061（未在讯问前要求律师）

**题目**（ZH，事实题）：“在羁押讯问开始前我没有主动要求律师。这个沉默本身是否等于放弃律师权，因而警察无需先作 Miranda 告知，就能把我后来作出的回答视为有效放弃？”

**检索 query**：`Miranda rights and the effect of silence during custodial interrogation on waiver of right to counsel`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-26.pdf/p0018/0031` | 0.30133163928985596 | 部分能（Miranda 告知是主要保护） |
| `chapter-26.pdf/p0014/0025` | 0.31172746419906616 | 能（不得从沉默或最终取得供述推定放弃） |
| `chapter-26.pdf/p0013/0022` | 0.31550300121307373 | 能（先有充分告知、理解和行使机会） |
| `chapter-25.pdf/p0022/0034` | 0.3250190019607544 | 不能（教材提示） |
| `chapter-26.pdf/p0014/0023` | 0.3281428813934326 | 部分能（告知后可根据言行判断放弃） |

**回答是否准确：核心结论准确，但解释有瑕疵。** 模型正确说沉默本身不等于放弃、警察须先作 Miranda 告知；但它补充称有效放弃“typically requires an affirmative act”，这一表述过强，与同次 Top-3 关于 express or implied waiver 的文本不一致。作为事实题仍可保留，并记录该生成措辞问题。

### law-b062（完整告知后说明指定程序）

**题目**（ZH，事实题）：“警察已明确告知一名无力聘请律师的嫌疑人：他有权在讯问前和讯问中获得律师，如无力负担将获指定律师；在嫌疑人询问‘什么时候会指定’时，警察又说明指定程序会在其出庭时进行。这个补充说明本身会不会使先前完整的 Miranda 告知失效？”

**检索 query**：`Miranda warning content and the requirement for timely provision of appointed counsel`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-23.pdf/p0019/0031` | 0.28276216983795166 | 能（本题的多数规则：完整告知并不因该补充说明失效） |
| `chapter-23.pdf/p0019/0032` | 0.32995980978012085 | 不能（同案异议意见，主张相反） |
| `chapter-23.pdf/p0017/0027` | 0.33723753690719604 | 部分能（告知充分性的背景） |
| `chapter-23.pdf/p0014/0021` | 0.33736395835876465 | 部分能（四项 Miranda 告知） |
| `chapter-34.pdf/p0015/0027` | 0.3634796738624573 | 不能（不同的二阶段讯问问题） |

**回答是否准确：准确。** 重测以及用户多次真实前端实测均返回完整回答，结论为“补充说明不使已完整的告知失效”。Top-1、Top-3 直接陈述该多数规则；Top-2 是异议意见，模型能够正确区分。此前两次隔离审查命令只打印到 retrieve 后即退出，属于审查执行时的偶发采集异常，不应记为产品管线缺陷。

### law-b063（儿童年龄与羁押判断）

**题目**（ZH，事实题）：“一名 13 岁学生被从初中课堂带走，在封闭房间里接受警察和校方人员讯问，直到供述后才被告知可以离开。法院判断这是否属于 Miranda 意义上的‘羁押’时，可以不考虑孩子的年龄吗？”

**检索 query**：`Miranda custody for minors and whether a court may disregard the child's age when determining if Miranda custody existed`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `jdb-v-north-carolina-2011.mp3/0015` | 0.2584223747253418 | 能（音频中明确称年龄必须纳入） |
| `chapter-24.pdf/p0010/0016` | 0.3316761255264282 | 不能（反对意见） |
| `jdb-v-north-carolina-2011.mp3/0019` | 0.34273648262023926 | 部分能（庭辩中的客观情境讨论） |
| `jdb-v-north-carolina-2011.mp3/0035` | 0.3453277349472046 | 不能（反对年龄因素的庭辩） |
| `chapter-24.pdf/p0004/0008` | 0.3496561050415039 | 能（多数意见：儿童年龄适当影响 custody 分析） |

**回答是否准确：准确。** 模型清楚回答不得忽略年龄；Top-1 和 Top-5 均给出直接依据。此题虽引用了音频，但类别仍为文本事实题，不计入音频题配额。

### law-b064（普通交通拦截）

**题目**（ZH，事实题）：“警察因普通交通违法把我拦下，在我被逮捕前于路边询问常规问题。仅因停车期间我暂时不能开车离开，警察就必须先作 Miranda 告知吗？”

**检索 query**：`Miranda warnings required during routine traffic stops`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `jdb-v-north-carolina-2011.mp3/0043` | 0.37705928087234497 | 不能（庭辩中关于警告成本的讨论） |
| `chapter-23.pdf/p0014/0021` | 0.3953455686569214 | 部分能（羁押讯问才须告知） |
| `chapter-24.pdf/p0015/0025` | 0.3972778916358948 | 能（普通交通拦截是否为 custodial interrogation 的直接问题） |
| `chapter-23.pdf/p0022/0041` | 0.4095175266265869 | 部分能（Miranda 一般背景） |
| `chapter-24.pdf/p0013/0022` | 0.41077983379364014 | 部分能（该案下级法院处理） |

**回答是否准确：准确。** 它保留了“普通、路边、未逮捕”的限定，没有把所有交通拦截或后续升级拘束概括为无需告知。

### law-b065（非问句的功能等同讯问）

**题目**（ZH，事实题）：“我行使保持沉默权后，警察不直接提问，却故意在我听得到的地方讨论：如果没人说出地点，失踪儿童可能会死亡；他们知道这很可能促使我开口。仅因为这些话不是以问句形式说出，就能完全排除在 Miranda 的‘讯问’之外吗？”

**真实前端检索 query**：`Miranda warning and coercive tactics such as discussing consequences of silence`

| chunk | score | 能否直接支撑“functional equivalent of questioning” |
|---|---:|---|
| `chapter-25.pdf/p0004/0006` | 0.2808486223220825 | 能（讯问包括明示提问及其功能等同物；警察应知可能引出不利陈述的言行亦属讯问） |
| `chapter-34.pdf/p0016/0028` | 0.28439831733703613 | 不能（二阶段、先问后告知策略） |
| `chapter-30.pdf/p0022/0036` | 0.2977888584136963 | 部分能（流程图区分 custody、interrogation 与 Miranda） |
| `chapter-25.pdf/p0012/0019` | 0.30076104402542114 | 部分能（异议中的一般讯问/诱发不利陈述讨论） |
| `chapter-23.pdf/p0014/0021` | 0.3009025454521179 | 不能（四项告知） |

**回答是否准确：准确。** 真实前端的 Top-1 就是 Innis 对 interrogation 的直接定义；题干又明确给定警察知道该评论很可能促使嫌疑人开口，因此可稳定推出结论。此前报告误用了隔离库另一次调用的 Top-5，现已覆盖。

**追问回答的质量问题：** 后续被问及“这些块如何支撑结论”时，模型对 Top-2、Top-3、Top-4、Top-5 伪造了并不存在的英文引文；例如 `chapter-34.pdf/p0016/0028` 实际讨论的是两阶段、先问后告知策略，`chapter-30.pdf/p0022/0036` 实际只是流程图。该次追问还在“逻辑链条 →”处因生成长度上限停止。这不改变原题答案的依据（Top-1 已充分），但应将“模型事后解释引用”视为不可靠，不能用于审查证据。

### law-b066（卧底冒充狱友）

**题目**（ZH，事实题）：“我在监狱中时，一名卧底警察冒充另一名囚犯与我交谈；我以为他只是狱友，便自由地讲述了自己的犯罪行为，期间没有收到 Miranda 告知。该卧底警察的讯问本身是否违反 Miranda？”

**检索 query**：`Miranda rights and undercover officers posing as inmates`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-25.pdf/p0012/0019` | 0.3627042770385742 | 不能（反对意见） |
| `chapter-25.pdf/p0011/0017` | 0.3821169137954712 | 不能（反对意见） |
| `chapter-29.pdf/p0023/0044` | 0.38554471731185913 | 部分能（教材问题，提示第六修正案区分） |
| `chapter-25.pdf/p0010/0016` | 0.3872087597846985 | 能（从嫌疑人视角没有警察主导强制环境） |
| `chapter-25.pdf/p0013/0020` | 0.39296966791152954 | 能（Perkins 规则及第六修正案边界） |

**回答是否准确：准确。** 模型正确说明其结论限于嫌疑人确实以为对方是狱友、自由陈述的情境，并区分了已被起诉后可能涉及的第六修正案问题；Top-4/5 均可直接支撑。

## chapter-22~25.pdf 批次小结（待用户审核）

| 题号 | 结果 |
|---|---|
| b057 | 准确；Top-1/3/5 的组合规则足以推导，非检索缺陷。 |
| b058 | 准确；多个结果与题干事实结合可直接推导，非未召回。 |
| b059 | 准确；Connelly 多数规则命中。 |
| b060 | 准确；充分告知要求命中。 |
| b061 | 核心结论准确；“必须积极行为才可放弃”的附带表述过强。 |
| b062 | 准确；重测和真实前端均有完整回答，Top-1/3 是多数规则。 |
| b063 | 准确；音频 Top-1 与文本 Top-5 都直接支持。 |
| b064 | 准确；交通拦截直接文本排名第 3。 |
| b065 | 准确；Top-1 直接定义功能等同讯问。后续“解释引用”伪造 2–5 的引文，另记生成问题。 |
| b066 | 准确；Perkins 多数规则排名第 4、5。 |

## chapter-26~29.pdf 批次（b067~b070，2026-07-24，待用户审核）

本批按章节 chunk 量各取 1 题（第 26、27、28、29 章分别为 38、42、38、45 个 chunk）。以下均为真实 `law-eval` 管线的 Top-5 完整结果。

### law-b067（模糊提及律师）

**题目**（EN，事实题）：“During custodial interrogation, after receiving complete Miranda warnings, I say only: ‘Maybe I should talk to a lawyer.’ Does that statement itself invoke my Miranda right to counsel and require officers to stop questioning?”

**检索 query**：`Miranda right to counsel and whether saying 'Maybe I should talk to a lawyer' invokes it`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-26.pdf/p0017/0030` | 0.2951738238334656 | 能（模糊提及律师不要求停止；须明确请求） |
| `chapter-23.pdf/p0019/0031` | 0.29878318309783936 | 部分能（律师告知背景） |
| `chapter-26.pdf/p0018/0031` | 0.3176230788230896 | 能（律师权须被明确行使） |
| `chapter-27.pdf/p0007/0013` | 0.3266868591308594 | 部分能（明确行使后才须停止） |
| `chapter-26.pdf/p0020/0035` | 0.3334423303604126 | 不能（反对意见） |

**回答是否准确：核心结论准确。** 模型正确回答模糊表述不触发停止讯问。它额外说警方“must be prepared to clarify”，而原文只称澄清是 good practice、非宪法义务；该附带措辞不影响题目所问的核心结论，已记录为轻微生成表述问题。

### law-b068（明确请求律师后的警方重启）

**题目**（ZH，事实题）：“我在羁押讯问中明确说‘我要律师’，讯问随即停止。次日，警察在没有提供律师的情况下主动回来要求谈话；我又说不想和任何人谈，但看守告诉我‘必须谈’，随后警察取得供述。警方能把这份供述作为我有效放弃律师权的结果使用吗？”

**检索 query**：`在羁押讯问中，当被询问者明确表示要律师后，讯问是否可以继续进行以及后续如何处理`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-27.pdf/p0021/0038` | 0.3284466862678528 | 能（请求律师后、未提供律师而再讯问会强化强迫） |
| `chapter-26.pdf/p0018/0031` | 0.33054327964782715 | 能（Edwards：请求后讯问须停止） |
| `chapter-26.pdf/p0019/0032` | 0.3363085985183716 | 能（明确请求后须立即停止直至律师在场） |
| `chapter-27.pdf/p0021/0039` | 0.33792394399642944 | 部分能（反对意见中的再讯问风险） |
| `chapter-26.pdf/p0017/0030` | 0.3556327223777771 | 能（本题“我要律师”满足明确请求门槛） |

**回答是否准确：准确。** 五段中四段直接支持；模型没有把看守的“必须谈”误作自愿重新启动。

### law-b069（六岁生日与例行登记例外）

**题目**（EN，事实题）：“While I am in custody for suspected DUI and have not received Miranda warnings, an officer asks routine booking questions and then deliberately asks, ‘What was the date of your sixth birthday?’ to test my ability to perform mental calculation and use the response as evidence of intoxication. May the State treat that question as a nontestimonial routine-booking question?”

**检索 query**：`whether questions asked during booking can be treated as non-testimonial if they are used to assess mental capacity or intoxication`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-28.pdf/p0017/0030` | 0.3690716028213501 | 能（普通身份信息才属 booking exception） |
| `chapter-28.pdf/p0014/0024` | 0.3968992829322815 | 部分能（物理证据与证言性证据的区分） |
| `jdb-v-north-carolina-2011.mp3/0003` | 0.4247446060180664 | 不能（儿童 custody 庭辩） |
| `chapter-28.pdf/p0014/0025` | 0.43628525733947754 | 能（本案事实：六岁生日回答的内容可表明醉态） |
| `chapter-28.pdf/p0015/0026` | 0.44113945960998535 | 能（心智混乱的推论来自证言性行为而非物理证据） |

**回答是否准确：准确。** Top-1 给出例行登记例外边界，Top-4/5 直接给出六岁生日问题及其证言性理由；模型正确区分口齿含混的物理表现与回答内容所揭示的心智状态。

### law-b070（第六修正案的罪名特定性）

**题目**（ZH，事实题）：“我已因入室盗窃被正式起诉并有律师代理。警方随后就同一事件中发生、但我尚未被起诉的谋杀罪直接讯问我，并取得供述；两罪按 Blockburger 标准并非同一罪。仅因盗窃案的第六修正案律师权已经附着，这份关于谋杀案的供述就必须排除吗？”

**检索 query**：`Blockburger test for double jeopardy and whether a confession obtained in one case can be used in another case under the Sixth Amendment`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-29.pdf/p0020/0035` | 0.2580806016921997 | 能（已起诉罪名才附着；Blockburger 的同罪测试） |
| `chapter-29.pdf/p0022/0040` | 0.29671621322631836 | 不能（反对意见） |
| `chapter-29.pdf/p0016/0028` | 0.34836453199386597 | 能（律师权罪名特定，不同罪可被问询） |
| `chapter-29.pdf/p0017/0031` | 0.3698076605796814 | 部分能（引入 Cobb 的背景） |
| `chapter-29.pdf/p0022/0041` | 0.3738524913787842 | 不能（反对意见） |

**回答是否准确：准确。** 模型正确保留本题的两个条件——谋杀尚未被起诉、且按 Blockburger 不是同一罪——没有将结论泛化为可无条件绕开 Miranda 或 Massiah。

## chapter-26~29.pdf 批次小结（待用户审核）

| 题号 | 结果 |
|---|---|
| b067 | 核心准确；Top-1 直接支持。附带称警方需澄清，表述过强。 |
| b068 | 准确；明确请求律师后的警方主动重启受到多段直接规则限制。 |
| b069 | 准确；登记例外边界和六岁生日的证言性均命中。 |
| b070 | 准确；罪名特定性与 Blockburger 条件均命中。 |

## chapter-30~33.pdf 批次（b071~b074，2026-07-24，待用户审核）

本批按第 30、31、32、33 章 chunk 量各取一题，完成事实题目标。以下为真实端到端调用的完整 Top-5。

### law-b071（被动监听的线人）

**检索 query**：`Sixth Amendment right to counsel and whether spontaneous statements made by a defendant to an informant in custody can constitute a violation of this right`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-30.pdf/p0020/0032` | 0.27291959524154663 | 部分能（政府故意规避律师权才违反） |
| `chapter-30.pdf/p0011/0016` | 0.2780940532684326 | 能（须有超出被动倾听、故意诱发的行为） |
| `chapter-29.pdf/p0019/0034` | 0.282881498336792 | 部分能（律师权附着的前提） |
| `chapter-30.pdf/p0005/0006` | 0.2858129143714905 | 能（自发且未被政府诱发的陈述不违反） |
| `chapter-30.pdf/p0016/0025` | 0.28719276189804077 | 部分能（第六修正案放弃背景） |

**回答是否准确：准确。** 模型保留“仅被动倾听、没有提问或诱发”的限定，没有把所有线人转告一概视作可采。

### law-b072（Mapp 对州的适用）

**检索 query**：`美国宪法第四修正案关于搜查和扣押的规定，以及排除规则的法律依据`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-09.pdf/p0003/0006` | 0.3027098774909973 | 不能（中立司法官与令状） |
| `chapter-21.pdf/p0003/0004` | 0.3138258457183838 | 不能（Terry 合理怀疑） |
| `chapter-32.pdf/p0014/0026` | 0.3177010416984558 | 部分能（排除规则是威慑性制裁） |
| `chapter-33.pdf/p0018/0030` | 0.3199882507324219 | 部分能（排除规则的一般限制） |
| `chapter-31.pdf/p0011/0021` | 0.3278244137763977 | 部分能（异议中的排除规则依据） |

**回答是否准确：结论正确但本轮检索不充分。** 模型正确回答州不能以原文未明写为由拒绝排除；但本轮 Top-5 未召回直接说明 Mapp 对州适用的 `chapter-31.pdf/p0009/0016`，反而把 Top-5 的异议意见当作主要依据。该题保留为“正确答案在书内、retrieve 未给出直接依据”的回归样本。

### law-b073（knock-and-announce 的救济）

**检索 query**：`knock-and-announce rule and whether evidence obtained without compliance must be excluded`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-32.pdf/p0005/0007` | 0.2531813383102417 | 能（合法令状下证据非因未敲门而取得） |
| `chapter-32.pdf/p0006/0010` | 0.283385694026947 | 不能（反对意见） |
| `chapter-32.pdf/p0004/0006` | 0.2890031337738037 | 能（该违反与证据发现关联不足） |
| `chapter-32.pdf/p0004/0005` | 0.2943694591522217 | 能（排除的成本与威慑权衡） |
| `chapter-32.pdf/p0003/0003` | 0.2955271005630493 | 能（该规则不保护隐匿证据） |

**回答是否准确：准确。** 结论被 Top-1、3、4、5 直接支持，并明确限于本规则违反和有效令状的组合。

### law-b074（乘客不得代位主张排除）

**检索 query**：`美国宪法第四修正案关于搜查和扣押的规定，以及乘客是否可以主张排除令（exclusionary rule）以排除被扣押的证物`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-33.pdf/p0003/0004` | 0.31168150901794434 | 能（只限自身第四修正案权利受侵害者） |
| `chapter-32.pdf/p0014/0026` | 0.3165374994277954 | 部分能（排除规则一般目的） |
| `chapter-33.pdf/p0018/0030` | 0.3268781900405884 | 部分能（排除规则限制） |
| `chapter-21.pdf/p0003/0004` | 0.3295149803161621 | 不能（Terry 合理怀疑） |
| `chapter-33.pdf/p0001/0000` | 0.3296976685523987 | 部分能（排除规则的可用性受限） |

**回答是否准确：准确。** Top-1 直接排除代位主张；模型将结论恰当限于题干给出的“无车辆或物品利益”的乘客。

## chapter-30~33.pdf 批次小结（待用户审核）

| 题号 | 结果 |
|---|---|
| b071 | 准确；被动倾听与故意诱发的边界直接命中。 |
| b072 | 结论正确；Mapp 对州适用的直接段落未进 Top-5，检索不足。 |
| b073 | 准确；四段直接支持。 |
| b074 | 准确；Top-1 直接排除代位主张。 |

## 音频与音频定向无答案批次（b075~b078，2026-07-24，待用户审核）

### law-b075（Birchfield 录音中的自然消散论点）

**检索 query**：`Birchfield v. North Dakota case, judge's statement about blood alcohol dissipating over time, and applicant's lawyer response regarding search incident to arrest`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `chapter-13.pdf/p0016/0028` | 0.2895578145980835 | 部分能（血检与搜查附带逮捕结论） |
| `birchfield-v-north-dakota-2016.mp3/0000` | 0.31803369522094727 | 部分能（案件与无令状检测背景） |
| `birchfield-v-north-dakota-2016.mp3/0028` | 0.3242930769920349 | 能（自然消散可预测、非嫌疑人控制，迅速检测或申请令状） |
| `chapter-13.pdf/p0008/0014` | 0.364826500415802 | 部分能（McNeely/Birchfield 背景） |
| `birchfield-v-north-dakota-2016.mp3/0059` | 0.37353527545928955 | 部分能（令状可在医院途中取得的讨论） |

**回答是否准确：准确。** 题目明确要求概括申请人律师的庭辩观点，Top-3 是该观点的逐字音频依据；未把庭辩观点误作法院最终 holding。

### law-b076（Carpenter 开场陈述）

**检索 query**：`In the Carpenter v. United States oral argument, what information did counsel say the government collected without a warrant, and over what period?`

| chunk | score | 能否直接支撑 |
|---|---:|---|
| `carpenter-v-united-states-2017.mp3/0000` | 0.34939032793045044 | 能（127 天 CSLI、地点/活动/关联） |
| `chapter-30.pdf/p0008/0011` | 0.39922529458999634 | 不能（Massiah） |
| `chapter-05.pdf/p0002/0003` | 0.4217110276222229 | 部分能（CSLI 的案件事实） |
| `chapter-30.pdf/p0003/0003` | 0.4272637367248535 | 不能（Massiah） |
| `carpenter-v-united-states-2017.mp3/0036` | 0.43658536672592163 | 部分能（第三方记录庭辩） |

**回答是否准确：准确。** Top-1 直接给出问题所求的信息和时长。

### law-b077（私营雇主酒精测试）——音频定向无答案题

**题目**："一家北达科他州私营物流公司规定，员工若在下班后的私人聚会饮酒，次日上班前必须接受呼气酒精测试；拒绝测试即被解雇。该员工能否依据联邦就业法获得违法解雇赔偿？"

**检索 query**：`北达科他州私营物流公司规定员工在私人聚会饮酒后次日上班前必须接受呼气酒精测试，拒绝则被解雇，该行为是否违反联邦就业法并导致赔偿`

| chunk | score | 能否推出私营物流雇主的联邦就业法赔偿 |
|---|---:|---|
| `chapter-13.pdf/p0008/0014` | 0.4137345552444458 | 不能（醉驾检测背景） |
| `birchfield-v-north-dakota-2016.mp3/0028` | 0.4172211289405823 | 不能（政府酒精检测庭辩） |
| `chapter-17.pdf/p0005/0008` | 0.41727572679519653 | 不能（联邦铁路安全监管） |
| `birchfield-v-north-dakota-2016.mp3/0000` | 0.4226253628730774 | 不能（政府道路检测法） |
| `chapter-17.pdf/p0006/0009` | 0.4260885715484619 | 不能（铁路事故后测试） |

**回答是否准确：不准确，未披露资料不足。** 模型把 FRA 铁路安全监管、醉驾检测和政府第四修正案庭辩类推为私营物流公司的联邦就业法规则，断言员工无权获赔；Top-5 均不提供私营雇佣、解雇、劳动保护或救济规则。该题保留为有效音频定向无答案题与高风险法律幻觉样本。

### law-b078（运营商向广告公司出售 CSLI）——音频定向无答案题

**题目**："在美国联邦法下，一家手机运营商未经用户许可，把客户连续 127 天的基站定位记录出售给一家广告公司。用户能否依据联邦数据保护法要求法定赔偿？"

**检索 query**（两次 retrieve）：

1. `美国联邦法下关于个人位置信息的收集、使用和出售的规定，特别是与《通信规范法案》或《隐私权法案》相关的内容`
2. `美国联邦数据保护法（如《隐私权法案》或《通信规范法案》）是否赋予个人对未经许可出售其位置信息的权利要求法定赔偿`

| retrieve | chunk | score | 能否推出私营数据出售的联邦法定赔偿 |
|---:|---|---:|---|
| 1 | `carpenter-v-united-states-2017.mp3/0011` | 0.4107135534286499 | 不能（运营商隐私政策对政府取得数据的庭辩） |
| 1 | `chapter-41.pdf/p0012/0019` | 0.4174047112464905 | 不能（FISA §1881a 的政府外国情报监控） |
| 1 | `carpenter-v-united-states-2017.mp3/0042` | 0.4178459048271179 | 不能（CSLI 的 customer proprietary information 与政府取得） |
| 1 | `carpenter-v-united-states-2017.mp3/0031` | 0.41857051849365234 | 不能（政府取得商业持有的基站记录） |
| 1 | `chapter-05.pdf/p0004/0006` | 0.42314743995666504 | 不能（政府长期取得 CSLI 的第四修正案） |
| 2 | `chapter-02.pdf/p0012/0021` | 0.39515525102615356 | 不能（第三方披露与第四修正案隐私理论） |
| 2 | `chapter-35.pdf/p0007/0016` | 0.4072245955467224 | 不能（民权诉讼费用背景，非运营商数据出售） |
| 2 | `carpenter-v-united-states-2017.mp3/0010` | 0.417572021484375 | 不能（是否自愿向运营商披露位置供政府取得） |
| 2 | `chapter-05.pdf/p0004/0006` | 0.41788578033447266 | 不能（政府长期取得 CSLI 的第四修正案） |
| 2 | `chapter-41.pdf/p0010/0016` | 0.4182889461517334 | 不能（FISA §1881a 的 standing 问题） |

**回答是否准确：有披露，但实体结论仍是外部补全。** 真实前端运行在结尾明确写道：“检索结果未提及任何关于‘法定赔偿’的具体条款或判例支持用户主张。”这已披露资料不足；按本测试集“只有完全不披露才计为幻觉”的统计口径，**不计入无披露幻觉**。但回答在此前仍确定断言用户不能获赔、把 Carpenter 说成政府取得运营商记录不构成搜查且客户没有合理隐私期待，并将政府取得 CSLI 的第四修正案材料延伸为私营运营商对广告公司出售数据的民事结论。两轮 10 个 chunk 都没有私营出售 CSLI 的适用联邦法、私人诉权或法定赔偿规则，无法推出这些断言。因此该题保留为有效音频定向无答案题及“有披露但仍夹带外部法律结论”的样本，而非无披露幻觉样本。

## 音频补充批次（b079~b082，2026-07-24，待用户审核）

### law-b079（J.D.B. 年龄是否需逐岁校准）——重出

**题目**："在 J.D.B. v. North Carolina 的庭审辩论中，Justice Scalia 追问申请人的规则是否要精细到 13 岁、13 岁半、14 岁等不同具体年龄。申请人律师是否要求法院按每一个具体年龄逐级校准羁押判断？"

**检索 query**：`在 J.D.B. v. North Carolina 案中，Justice Scalia 是否追问申请人律师是否要求按每个具体年龄（如13岁、13岁半、14岁）逐级校准羁押判断`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `jdb-v-north-carolina-2011.mp3/0001` | 0.2956300973892212 | 能（逐字说 “We did not suggest that it be calibrated by age”） |
| `jdb-v-north-carolina-2011.mp3/0000` | 0.30904144048690796 | 部分能（Scalia 提出一般未成年人规则还是不同年龄规则） |
| `jdb-v-north-carolina-2011.mp3/0045` | 0.3328589200973511 | 部分能（申请人主张年龄是客观情境之一，而非亮线规则） |
| `chapter-24.pdf/p0009/0014` | 0.34327155351638794 | 部分能（最终要求考虑 J.D.B. 年龄，但未直接回答逐岁校准） |
| `chapter-24.pdf/p0004/0008` | 0.3472668528556824 | 部分能（年龄适当影响羁押分析） |

**回答是否准确：准确。** 真实端到端运行的 Top-1 精确命中；模型明确回答“不主张按每个具体年龄逐级校准”，并复述了律师的原话。随后关于年龄作为相关情境的说明也没有改变这一核心答案。这一题替换原 b079，原题及其判定不再保留。

### law-b080（申请人是否要求另设儿童版 Miranda 文本）

**题目**："在 J.D.B. v. North Carolina 的辩论中，申请人是否主张必须为所有未成年人另设一套按年龄细分的 Miranda 警告文本？"

**检索 query**："J.D.B. v. North Carolina case, whether the petitioner argued for separate Miranda warnings tailored by age for minors"

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `jdb-v-north-carolina-2011.mp3/0000` | 0.29686009883880615 | 部分能（法官提出“是否要有不同的未成年人 Miranda 规则”的问题，但未给出申请人回答） |
| `jdb-v-north-carolina-2011.mp3/0006` | 0.34528112411499023 | 能（律师答“Not necessarily”，说明无需改变警告文本；年龄会影响有效放弃权利） |
| `jdb-v-north-carolina-2011.mp3/0035` | 0.35516369342803955 | 部分能（反方认为纳入年龄会使规则复杂，不能反驳申请人已明确表达的立场） |
| `chapter-24.pdf/p0006/0010` | 0.3577039837837219 | 部分能（案件事实：J.D.B. 后来才被告知可离开/拒答） |
| `chapter-24.pdf/p0009/0014` | 0.3642684817314148 | 部分能（法院要求州法院在羁押判断中考虑年龄） |

**回答是否准确：核心回答准确，不计为幻觉。** 模型正确回答“并未主张另设按年龄细分的警告文本”，也引用了 Top-2 的直接原话。其后对判决的概括不够严谨，但用户复核认为 `chapter-24.pdf/p0009/0014` 的表述本身不清晰，不能将该处归为模型与原文的可稳定判定冲突；因此保留为回答质量备注，不纳入幻觉统计。

### law-b081（拒绝无令状化学检测的后果）

**题目**："在 Birchfield v. North Dakota 的辩论开场，北达科他州和明尼苏达州的相关法律如何处理酒驾嫌疑人拒绝接受无令状化学检测？"

**检索 query**："Birchfield v. North Dakota case, how do North Dakota and Minnesota laws handle refusal to submit to chemical testing without a warrant for DUI suspects"

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `birchfield-v-north-dakota-2016.mp3/0000` | 0.2255914807319641 | 能（开场律师逐字称两州法律使拒绝无令状化学检测成为刑事犯罪） |
| `chapter-13.pdf/p0016/0028` | 0.30311518907546997 | 部分能（Birchfield 因拒绝无令状抽血被刑事起诉，且该项定罪被撤销） |
| `chapter-13.pdf/p0010/0018` | 0.306782603263855 | 能（北达科他州法明确称拒绝测试会面临刑事处罚） |
| `chapter-13.pdf/p0008/0014` | 0.3076690435409546 | 部分能（背景性说明各州酒精测试与拒绝的驾照后果） |
| `chapter-13.pdf/p0010/0019` | 0.32609039545059204 | 部分能（说明案件围绕能否因拒绝无令状测试定罪） |

**回答是否准确：题目所问的开场立场准确，但真实前端回答含实质性错误扩展。** 三次持久化的真实端到端回答均正确复述 Top-1/Top-3：两州将拒绝测试定为犯罪并可能施加刑事处罚；但随后一致断言最高法院已裁定所有此类无令状检测违反第四修正案、拒绝均不能刑事化。该概括既超出“辩论开场”的题目范围，也抹去了 blood/breath 的决定性区分，不能由本次引用支撑。因此 b081 保留为有答案题中的一例生成幻觉；题目本身仍保留，因为其标准答案和音频依据稳定。

### law-b082（呼气测试为何与令状机制不匹配）

**题目**："In the Birchfield v. North Dakota argument, why did the advocate opposing a warrant requirement for breath tests say that a warrant is an awkward fit?"

**检索 query**：`Birchfield v. North Dakota argument regarding warrant requirement for breath tests and why it was considered an awkward fit`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-13.pdf/p0016/0028` | 0.2851518988609314 | 不能（无令状抽血的最终处理，不解释“令状为何不适配呼气”） |
| `birchfield-v-north-dakota-2016.mp3/0057` | 0.29856663942337036 | 能（逐字说明：令状不能让人持续呼气，故不适配） |
| `birchfield-v-north-dakota-2016.mp3/0000` | 0.3428170084953308 | 部分能（案件与无令状测试背景） |
| `birchfield-v-north-dakota-2016.mp3/0016` | 0.3439546823501587 | 部分能（申请人反对把呼气测试视为搜查附带逮捕） |
| `birchfield-v-north-dakota-2016.mp3/0033` | 0.3484957814216614 | 部分能（北达科他州方谈一般令状实践困难） |

**回答是否准确：准确。** 模型抓住 Top-2 的限定理由：呼气检测需要持续的生理配合，令状不能让警察强制一个人足够稳定地呼气；其余“中立法官审查”“通常令状可以强制执行”的解释也仍在 Top-2 内容范围内。没有把律师主张误写成法院最终裁判。

## chapter-18~19.pdf 补充审查（b044~b047，2026-07-24，待用户审核）

### law-b044（库存搜查中的上锁行李箱）

**题目**："Police lawfully impound my car and inventory it under department practice. They find a locked suitcase in the trunk, but the department has no standardized criteria or established routine on opening closed containers during inventories. May they open the suitcase anyway just because it is an inventory search?"

**检索 query**：`inventory search and opening closed containers under police department practice`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-18.pdf/p0012/0024` | 0.38469576835632324 | 能（Florida v. Wells 逐字规定：无既定标准/惯例时打开后备箱上锁行李箱违反第四修正案） |
| `chapter-18.pdf/p0012/0023` | 0.40006089210510254 | 部分能（例行登记的合法目的与标准化程序） |
| `chapter-09.pdf/p0018/0033` | 0.4020950198173523 | 不能（probable cause 下的汽车例外） |
| `chapter-10.pdf/p0015/0027` | 0.4029545187950134 | 不能（逮捕附带搜查） |
| `chapter-09.pdf/p0020/0035` | 0.4162158966064453 | 不能（汽车例外下的容器范围） |

**回答是否准确：准确。** Top-1 逐字覆盖题干的上锁行李箱、inventory 与缺少标准化标准三项条件；模型没有把其他汽车搜查例外混入理由。

### law-b045（例行登记时采集 DNA 口腔拭子）

**题目**："After police have probable cause to arrest me and take me into custody, they collect a DNA cheek swab during routine booking to confirm my identity and compare it with records already lawfully held by police. Is that collection necessarily unconstitutional merely because officers have no separate warrant for the swab?"

**检索 query**：`constitutionality of DNA cheek swab collection during routine booking without a separate warrant`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-18.pdf/p0024/0044` | 0.35870832204818726 | 能（合法羁押下口腔拭子的低侵入性与 DNA identification 合理性） |
| `chapter-18.pdf/p0020/0039` | 0.38003963232040405 | 能（严重罪名合法逮捕后的口腔拭子与合理性标准） |
| `chapter-18.pdf/p0019/0038` | 0.3933107256889343 | 能（口腔拭子程序及仅作身份识别的限制） |
| `chapter-13.pdf/p0002/0004` | 0.4089165925979614 | 不能（酒驾抽血） |
| `chapter-13.pdf/p0003/0006` | 0.4125209450721741 | 不能（酒驾抽血的紧急情形） |

**回答是否准确：准确。** 回答限于题干给出的合法羁押、例行登记与身份识别条件；没有把 DNA 拭子泛化为所有情境下均不需令状。

### law-b046（追逐中丢弃毒品）

**题目**："An officer shouts for me to stop, but I keep running. The officer has not touched me, and I have not submitted to authority. Before officers tackle me, I throw away a bag of drugs. Had I already been seized under the Fourth Amendment when I discarded the bag?"

**检索 query**：`Fourth Amendment seizure definition and when it occurs, particularly in relation to discarding contraband during pursuit`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-19.pdf/p0001/0000` | 0.30060720443725586 | 部分能（本章的 seizure 定义背景） |
| `chapter-19.pdf/p0007/0012` | 0.30701708793640137 | 能（Hodari D. 的 physical force / control 与丢弃物时点） |
| `chapter-19.pdf/p0008/0015` | 0.3346371650695801 | 不能（反对意见） |
| `chapter-19.pdf/p0007/0013` | 0.3535633087158203 | 能（show of authority 未获服从不构成 seizure） |
| `chapter-21.pdf/p0023/0045` | 0.36469948291778564 | 部分能（第四修正案救济流程图） |

**回答是否准确：准确。** Top-2、Top-4 直接支持“未被物理控制且未服从命令前，不构成 seizure”；模型据此正确回答丢弃发生在 seizure 之前。

### law-b047（轻罪现场逮捕）

**题目**："An officer sees me commit a minor misdemeanor in the officer's presence. State law would prefer a citation rather than a custodial arrest, but the officer arrests me without a warrant. Does the Fourth Amendment itself forbid the arrest merely because the offense is minor or state law would have allowed only a citation?"

**检索 query**：`Fourth Amendment and arrest for minor misdemeanor without warrant`

| chunk | score | 能否支撑答案 |
|---|---:|---|
| `chapter-19.pdf/p0011/0021` | 0.29977381229400635 | 部分能（现场轻罪逮捕的普通法与州法背景） |
| `chapter-19.pdf/p0012/0022` | 0.3027292490005493 | 能（Atwater 明确裁定第四修正案不禁止轻罪无令状逮捕） |
| `chapter-19.pdf/p0016/0029` | 0.31383681297302246 | 能（州可立法设更严格的小罪逮捕限制） |
| `chapter-13.pdf/p0020/0034` | 0.3253171443939209 | 不能（住宅内轻罪的紧急情形） |
| `chapter-12.pdf/p0011/0020` | 0.32591885328292847 | 不能（住宅无令状进入） |

**回答是否准确：准确。** 旧报告的“多数意见未命中、混入反对意见”是缺失逐题审查时的错误概括，现已覆盖：Top-2 即为多数意见的直接结论，Top-3 直接说明州可设置更严格限制而不改变联邦第四修正案标准。

## 最终中文无答案批次（b083~b085，2026-07-24，待用户审核）

### law-b083（私立医院泄露诊断信息）

**题目**："一家私立医院未经患者同意，把其诊断信息发送给患者的雇主。患者能否仅依据 HIPAA 在联邦法院直接请求法定赔偿？"

**检索 query**：`HIPAA 下患者能否在联邦法院直接请求法定赔偿`

| chunk | score | 能否支撑 HIPAA 的私人诉权或法定赔偿 |
|---|---:|---|
| `chapter-36.pdf/p0005/0008` | 0.46429502964019775 | 不能（刑事被告在直接上诉后取得律师的问题） |
| `chapter-35.pdf/p0007/0016` | 0.47061920166015625 | 不能（第四修正案民权诉讼的律师费） |
| `chapter-41.pdf/p0011/0017` | 0.4762308597564697 | 不能（FISA 监控的 Article III standing） |
| `chapter-35.pdf/p0009/0019` | 0.4775325655937195 | 不能（警察过度武力与合格豁免） |
| `chapter-12.pdf/p0014/0029` | 0.479386568069458 | 不能（紧急救助例外） |

**回答是否准确：准确披露资料不足。** 模型明确说明所有命中内容均非 HIPAA 或医疗隐私法，拒绝从中判断是否有联邦私人诉权或法定赔偿；没有用训练知识替代检索结果。该题是有效无答案题。

### law-b084（申请破产前的奢侈消费）

**题目**："个人在申请美国 Chapter 7 破产前一周用信用卡购买奢侈品，该笔债务是否当然可以在破产程序中免责？"

**检索 query**：`Chapter 7 bankruptcy 中关于债务免责的规则，特别是针对破产申请前一周内使用信用卡购买奢侈品的情况`

| chunk | score | 能否支撑 Chapter 7 的免责例外 |
|---|---:|---|
| `chapter-15.pdf/p0001/0000` | 0.4336012005805969 | 不能（令状例外章节标题） |
| `carpenter-v-united-states-2017.mp3/0023` | 0.4804585576057434 | 不能（庭辩中把信用卡消费举作第三方记录的类比） |
| `chapter-16.pdf/p0001/0000` | 0.4937285780906677 | 不能（令状例外章节标题） |
| `chapter-10.pdf/p0001/0000` | 0.4991763234138489 | 不能（令状例外章节标题） |
| `chapter-12.pdf/p0001/0000` | 0.5035165548324585 | 不能（令状例外章节标题） |

**回答是否准确：披露检索不足，但夹带外部法条结论。** 模型先明确称没有直接规则，随后援引《破产法》第 523 条并断言债务“不能当然免责”。Top-5 没有破产法、免责例外、奢侈消费或适用门槛，不能支撑该结论；按披露口径不计为无披露幻觉。该题保留为有效无答案题。

### law-b085（纽约州反 SLAPP 律师费）

**题目**："一家餐厅因顾客在网上发布负面评价而提起诽谤诉讼。顾客能否依据纽约州反 SLAPP 法要求餐厅支付律师费？"

**检索 query**：`New York State anti-SLAPP law and whether a customer can recover attorney fees for defamation claims against a restaurant`

| chunk | score | 能否支撑纽约反 SLAPP 的律师费救济 |
|---|---:|---|
| `chapter-35.pdf/p0007/0016` | 0.4861825704574585 | 不能（第四修正案民权诉讼律师费） |
| `chapter-20.pdf/p0021/0041` | 0.5023789405822754 | 不能（纽约 stop-and-frisk 的种族偏见争议） |
| `chapter-18.pdf/p0017/0034` | 0.5070119500160217 | 不能（酒店记录的行政搜查） |
| `chapter-01.pdf/p0014/0028` | 0.5108547806739807 | 不能（警察侵权案件和解） |
| `chapter-35.pdf/p0007/0015` | 0.5157061219215393 | 不能（宪法侵权诉讼的律师费和代理） |

**回答是否准确：准确披露资料不足。** 模型指出命中块没有纽约反 SLAPP、诽谤或该州律师费规则，结论限定为“资料不足以判断”，未自行回答州法实体问题。该题是有效无答案题。

## 总体统计（2026-07-29更新）

题库原始共 85 题：事实题 64、无答案题 13、音频题 8；中文 39、英文 46。音频题为中文 4、英文 4。`law-b009` 于2026-07-29在自动GPU路径连续3次完整披露资料不足，现已重新纳入质量/幻觉统计，评估总样本为 **85 题**。

**指标口径**：Hit@5 只对有答案题（事实题和音频题，共 72 道）统计，要求本次真实运行返回的 Top-5 中至少有一个 chunk 能直接或与题干事实结合推出标准答案；不以“模型凭训练知识碰巧答对”计为命中。无答案题不适用 Hit@5。**全量幻觉率**的分母为可评估的 85 题：有答案题中，回答作出与本书支持结论冲突的断言、虚构来源内容或加入影响结论的无依据扩展，计为一题；无答案题中，检索资料不足时仍作出确定实体结论且不明确承认资料不足，计为一题。单纯检索未命中但主结论碰巧正确的题目不计入幻觉，另由 Hit@5 反映。无披露幻觉率是全量幻觉率中的无答案子集；“有披露但仍夹带块外结论”另列。

- **Hit@5：67/72 = 93.1%**。未由实际 Top-5 支撑的 5 道为：`law-b002`（Jones 多数依据未命中）、`law-b003`（Greenwood 垃圾场景完全未命中）、`law-b016`（Ybarra 规则未命中）、`law-b048`（Rodriguez 规则未命中）、`law-b072`（Mapp 对州适用的直接依据未命中）。其中 b002/b016/b048/b072 的模型主结论可能正确，但不计为检索命中。
- **全量幻觉率：5/85 = 5.9%**。有答案题的 3 道为：`law-b003`（检索完全偏离垃圾搜查场景后得出错误结论）、`law-b016`（未命中 Ybarra 规则且伪称多个原文段落直接支持）、`law-b081`（真实前端回答把只支持开场律师立场的材料扩展为不区分 blood/breath 的终局裁判）。无答案题的 2 道为 `law-b056`、`law-b077`，见下一项。重出的 `law-b079` 已准确作答；`law-b080` 因其被质疑处的 chunk 表述不清晰，不计为模型幻觉。`law-b002`、`law-b048`、`law-b072` 虽未召回决定性依据，但主结论未被判为实体幻觉；`law-b009` 现计为正确披露资料不足。
- **无答案题无披露幻觉率：2/13 = 15.4%**。`law-b056` 在没有 first-sale doctrine 依据时确定作答；`law-b077` 把铁路/醉驾/政府搜查材料类推为私营物流雇佣法，并断言员工无权获赔。
- **有披露但仍作块外补全：4/13 = 30.8%**。`law-b010`、`law-b019`、`law-b078`、`law-b084` 都明确承认当前检索不足，但又加入未由命中块支撑的州法、隐私法或破产法结论；这不计为无披露幻觉，但不符合“严格依据检索作答”的要求。
- **正确披露资料不足：7/13 = 53.8%**。`law-b009`、`law-b020`、`law-b041`、`law-b042`、`law-b055`、`law-b083`、`law-b085` 明确限定为无法依据当前资料判断，未把外部法律知识伪装为本书结论。

以上无答案质量比例的分母均为 13；三类可判定结果（无披露幻觉 2、有披露越界 4、正确披露 7）共同覆盖全部无答案题。
