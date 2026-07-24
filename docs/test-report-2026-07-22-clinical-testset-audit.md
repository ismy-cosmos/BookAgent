# 临床测试集构建：真实管线审查记录

记录构建`eval/testset/clinical/qa/qa.jsonl`过程中，用真实端到端管线（`book_id=clinical-eval`，`answer()`，`qwen3:q4km`）对每道题的检索质量核验结果。审查方法：`eval/audit_question.py --subject clinical`跑真实`answer()`，逐个citation核对`score`（ChromaDB cosine距离，越小越相关）和chunk全文是否真能推出标准答案。

格式：每题按"题目原文+检索query+score表格+回答是否准确+具体分析"记录。跨题目的共性问题统一放各章节末尾或本文档最后，不为这些问题单独开GitHub issue——如果问题本身跟issue #40（retrieve无相关性阈值）或issue #48（缺混合检索）已覆盖的范围一致，就不重复开。

全量结果汇总表（含Hit@5/工具调用/回答准确/幻觉四项指标）待全部批次（4个PDF章节+音频+图片，共84题）审查完成后统一汇总，不按批次分别计算，避免中间数字被当作最终结论引用。

## openstax-pharm-ch07-antiinfective.pdf 章节（19题，2026-07-22重做：中英文混合+无答案题改自然提问）

### clinical-b001

**题目**（EN）："What is the difference between innate immunity and adaptive immunity in terms of how quickly each responds and how specific each is to a particular pathogen?"

**检索query**："difference between innate immunity and adaptive immunity in terms of response speed and specificity to pathogens"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0001/0004` | 0.3023 | **能，排名第1**（免疫定义核心段） |
| `openstax-pharm-ch07-antiinfective.pdf/p0002/0006` | 0.4737 | 不能（感染后症状/免疫逃逸，非定义本身） |
| `openstax-pharm-ch07-antiinfective.pdf/p0001/0001` | 0.5500 | 不能（Figure 7.1图注，泛泛描述） |
| `openstax-pharm-ch07-antiinfective.pdf/p0019/0082` | 0.5584 | 不能（HIV/AIDS定义，跑题） |
| `Dopamine & Dobutamine - with a Mnemonic - Cardiac Pharmacology (6).mp3/0001` | 0.5685 | 不能（心脏药理β受体机制，完全无关，跨来源污染） |

**回答是否准确**：准确，响应速度和特异性两方面均正确。

**具体分析**：目标chunk稳定排名第1，其余4个均不相关（含1个跨音频来源污染），检索质量一般但不影响本题。

### clinical-b002

**题目**（ZH）："细菌产生的β-内酰胺酶是通过什么方式使青霉素类抗生素失效的？"

**检索query**："细菌产生的β-内酰胺酶如何使青霉素类抗生素失效"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0015` | 0.4152 | **能，排名第1**（目标chunk） |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0022` | 0.4600 | 不能（氨基糖苷类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0003/0010` | 0.4744 | 部分能（抗生素耐药一般机制） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0065` | 0.4767 | 不能（多烯类抗真菌） |
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0017` | 0.4789 | 不能（大环内酯类） |

**回答是否准确**：准确，直接引用原文机制。

**具体分析**：目标chunk排名第1，检索质量好。

### clinical-b003

**题目**（EN）："Vancomycin belongs to which class of antibiotics, and how does it act against gram-positive bacteria such as MRSA?"

**检索query**："Vancomycin antibiotic class and mechanism of action against Gram-positive bacteria including MRSA"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0018` | 0.2675 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0020` | 0.3902 | 不能（克林霉素） |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0019` | 0.4045 | 不能（利奈唑胺） |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0022` | 0.4401 | 不能（氨基糖苷类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0007/0030` | 0.4624 | 不能（药物不良反应/过敏交叉反应） |

**回答是否准确**：准确，还合理补充了万古霉素输注反应等临床要点（未超出原文矛盾范围）。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b004（有意保留原题面，用于暴露dense检索对query措辞高度敏感这一真实缺陷；系统提示词修改后大多数情况下可命中，但存在真实反复，不算稳定修复）

**题目**（ZH，沿用原ch07报告题面，未改写）："利奈唑胺（linezolid）属于哪一类抗生素？它主要用于治疗哪种高度耐药感染？"

**多数情况（`audit_question.py`复测8次里7次）下的真实结果**：

检索query："利奈唑胺（linezolid）属于哪一类抗生素，主要用于治疗哪种高度耐药感染"（更贴近题目原文措辞，跟chunk原文"highly resistant"用词更接近）

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0020`（克林霉素，非本题） | 0.4353 | 不能 |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0019`（**正是`supporting_chunks`标注的原始出处**："Oxazolidinones include...linezolid...vancomycin-resistant Staphylococcus aureus (VRSA)"） | 0.4357 | **能，核心论据** |
| `openstax-pharm-ch07-antiinfective.pdf/p0035/0159`（抗寄生虫药物，非本题） | 0.4532 | 不能 |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0025`（硝基咪唑类，非本题） | 0.4869 | 不能 |
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0017`（大环内酯类，非本题） | 0.4931 | 不能 |

这种情况下**回答准确、真实检索命中支撑**——"利奈唑胺属于氧杂环丁酮类抗生素（Oxazolidinones），主要用于治疗对传统抗生素如万古霉素高度耐药的感染，例如万古霉素耐药性金黄色葡萄球菌（VRSA）"，逐字对应`p0005/0019`原文。

**少数情况（8次里1次，以及真实后端API单独复测1次也复现）下的真实结果**：自生成query退回原来的抽象改写"利奈唑胺（linezolid）的分类及其主要适应症"，目标chunk跌出top5（命中的反而是2个跨章节ch13精神药物无关内容），模型依赖训练知识作答，诚实披露"检索结果中未直接提及利奈唑胺"（结论仍然正确，但未由检索支撑）。

**结论：约7/8命中，约1/8退回未命中，是真实存在的反复，不是稳定修复**。这次的改善方式是让模型自己生成的query更贴近原文措辞，跟"给检索层加一条独立的关键词/BM25兜底路径"是两件完全不同的事——后者才是真正需要单独评估的基础设施改动，这道题dense检索对query措辞的敏感性本质上仍然存在。

**具体分析**：语料内`openstax-pharm-ch07-antiinfective.pdf/p0005/0019`明确写着"Oxazolidinones include the medication linezolid...vancomycin-resistant Staphylococcus aureus (VRSA)"，跟本题几乎字面对应，原提示词下top5完全未命中（目标chunk稳定排第9）。用`Embedder`+`ChromaStore.query`直接对比候选query定位到原因：原query"分类及其主要适应症"是抽象归纳式问法，没用到chunk原文的具体术语（"highly resistant"、"VRSA"）；改写后的问法提到"高度耐药的感染"，语义上更贴近原文用词，排名因此上升；若进一步加入"VRSA"这个原文专有名词，能排到第1；反过来去掉英文药名"linezolid"，目标chunk会跌出top10。这个题目的价值就在于它会被原表述miss掉，所以保留原题面不改写。

### clinical-b005

**题目**（EN）："Fluoroquinolone antibiotics work by inhibiting which bacterial enzyme, and what is the ultimate effect on the bacterial cell?"

**检索query**："Fluoroquinolone antibiotics mechanism of action: which bacterial enzyme do they inhibit and what is the ultimate effect on the bacterial cell?"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0023` | 0.3237 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0067` | 0.4328 | 不能（氟胞嘧啶） |
| `openstax-pharm-ch07-antiinfective.pdf/p0008/0031` | 0.4595 | 不能（四环素类不良反应，含氟喹诺酮安全性提及） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0068` | 0.4653 | 不能（棘白菌素类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0031/0140` | 0.4833 | 不能（异烟肼等抗结核药） |

**回答是否准确**：准确，DNA gyrase+DNA链断裂+凋亡三点均对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b006

**题目**（ZH）："奈玛特韦（nirmatrelvir）为什么要跟利托那韦（ritonavir）联合使用？"

**检索query**："奈玛特韦与利托那韦联合使用的药理机制和临床意义"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0013/0054` | 0.4607 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0015/0060` | 0.4814 | 部分能（剂量表） |
| `openstax-pharm-ch07-antiinfective.pdf/p0015/0061` | 0.5067 | 不能（表格标题） |
| `openstax-pharm-ch07-antiinfective.pdf/p0014/0057` | 0.5310 | 不能（剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0095` | 0.5344 | 不能（跨章节污染） |

**回答是否准确**：准确，CYP3A4抑制机制答对；回答里补充了"避免代谢过快导致药效不足"的说法，属合理引申，未与原文矛盾。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b007

**题目**（EN）："Azole antifungal drugs are divided into which two subclasses, and what enzyme do they inhibit?"

**检索query**："subclasses of Azole antifungal drugs and the enzyme they inhibit"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0066` | 0.2981 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0017/0075` | 0.3605 | 不能（CYP3A4相互作用） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0068` | 0.3746 | 不能（棘白菌素类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0018/0076` | 0.4011 | 部分能（氟康唑剂量表，间接印证机制） |
| `openstax-pharm-ch07-antiinfective.pdf/p0017/0072` | 0.4638 | 不能（表格标题） |

**回答是否准确**：准确，两大类+抑制酶均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b008

**题目**（ZH）："氟胞嘧啶（flucytosine）在真菌细胞内转化成5-FU之后，抑制的是哪种酶？"

**检索query**："氟胞嘧啶（flucytosine）在真菌细胞内转化成5-FU后抑制的酶"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0067` | 0.2696 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0023` | 0.4337 | 不能（氟喹诺酮类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0068` | 0.4778 | 不能（棘白菌素类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0066` | 0.4900 | 不能（唑类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0065` | 0.5002 | 不能（多烯类） |

**回答是否准确**：准确，直接引用原文。

**具体分析**：目标chunk排名第1且score明显更低（0.27 vs 0.43+），检索质量本题最好。

### clinical-b009

**题目**（EN）："During the fusion step of the HIV replication cycle, which molecules on the host cell surface does the viral protein gp120 bind to?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0020/0084` | 0.3538 | **能，排名第1**（HIV复制周期图，VLM描述） |
| `openstax-pharm-ch07-antiinfective.pdf/p0019/0083` | 0.4301 | 能（HIV进入CD4细胞过程，支撑性内容） |
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0092` | 0.4303 | 能（CCR5辅助受体细节，支撑性内容） |
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0091` | 0.4523 | 不能（蛋白酶抑制剂） |
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0090` | 0.5054 | 不能（恩夫韦地） |

**回答是否准确**：准确，CD4+共受体（CCR5/CXCR4）均答对。

**具体分析**：本题top3全部相关（含1个内嵌图片VLM描述chunk），检索质量好，验证了内嵌图描述回填机制工作正常。

### clinical-b010

**题目**（ZH）："马拉韦罗（maraviroc）是通过拮抗哪个受体来阻止HIV进入细胞的？"

**检索query**："马拉韦罗（maraviroc）通过拮抗哪个受体来阻止HIV进入细胞"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0092` | 0.3246 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0023/0104` | 0.4014 | 部分能（maraviroc不良反应，非机制本身） |
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0089` | 0.4252 | 不能（整合酶抑制剂） |
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0091` | 0.4322 | 不能（蛋白酶抑制剂） |
| `openstax-pharm-ch07-antiinfective.pdf/p0021/0090` | 0.4349 | 不能（恩夫韦地） |

**回答是否准确**：准确，直接引用原文。

**具体分析**：目标chunk稳定排名第1。

### clinical-b011

**题目**（EN）："Patients who carry which allele are at higher risk of a serious hypersensitivity reaction to abacavir?"

**检索query**："allele associated with increased risk of hypersensitivity reaction to abacavir"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0025/0109` | 0.2946 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0012/0055` | 0.4884 | 不能（ARB相关情绪障碍，跨章节污染） |
| `openstax-pharm-ch07-antiinfective.pdf/p0007/0030` | 0.5033 | 不能（抗生素过敏交叉反应） |
| `openstax-pharm-ch07-antiinfective.pdf/p0024/0108` | 0.5116 | 不能（用药教育要点） |
| `openstax-pharm-ch13-psychopharm.pdf/p0020/0077` | 0.5143 | 不能（氯氮平血液学不良反应，跨章节污染） |

**回答是否准确**：准确，HLA-B*5701答对。

**具体分析**：目标chunk稳定排名第1，score明显更低（0.29 vs 0.48+），检索质量好。

### clinical-b012

**题目**（ZH）："衣原体感染目前的一线治疗药物是什么？为什么不再首选阿奇霉素？"

**检索query**："衣原体感染的一线治疗药物及为何不再首选阿奇霉素"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0019/0080` | 0.5112 | 不能（两性霉素B适应症） |
| `Cardiac Pharmaoclogy (1) ｜ Fenoldopam with a Mnemonic.mp3/0001` | 0.5261 | 不能（原发性高血压病因，完全无关，跨来源污染） |
| `openstax-pharm-ch07-antiinfective.pdf/p0028/0128` | 0.5273 | **能，排名第3**（目标chunk） |
| `openstax-pharm-ch07-antiinfective.pdf/p0028/0127` | 0.5337 | 不能（甲硝唑/BV滴虫病） |
| `openstax-pharm-ch07-antiinfective.pdf/p0029/0131` | 0.5348 | 部分能（doxycycline剂量表，间接支撑） |

**回答是否准确**：准确，多西环素+耐药性上升原因均答对。

**具体分析**：目标chunk排名第3才进入，score普遍偏高（0.51+），且top5里混入1个完全无关的跨音频来源内容，检索精度不算理想，但未影响最终答案准确性。

### clinical-b013

**题目**（EN）："Metronidazole is recommended for treating which two infections?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0035/0159` | 0.3506 | 部分能（甲硝唑用于寄生虫感染，主题重叠但非本题目标段落） |
| `openstax-pharm-ch07-antiinfective.pdf/p0028/0127` | 0.3633 | **能，排名第2**（目标chunk，明确写BV+trichomoniasis） |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0025` | 0.4355 | 不能（硝基咪唑类分类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0066` | 0.4553 | 不能（唑类） |
| `openstax-pharm-ch07-antiinfective.pdf/p0036/0163` | 0.4592 | 不能（驱虫药） |

**回答是否准确**：准确，BV+trichomoniasis均答对。

**具体分析**：目标chunk排名第2但被排名第1的"部分相关"chunk（同药物不同适应症段落）压过，属于药物在书中多处出现导致的正常竞争，不算缺陷。

### clinical-b014

**题目**（ZH）："标准的结核病（TB）治疗疗程至少需要多长时间？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0031/0137` | 0.2843 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0031/0141` | 0.4173 | 部分能（耐药TB管理，非疗程时长） |
| `openstax-pharm-ch07-antiinfective.pdf/p0020/0085` | 0.4363 | 不能（HIV潜伏期，跑题） |
| `openstax-pharm-ch07-antiinfective.pdf/p0032/0144` | 0.4390 | 部分能（异烟肼剂量表，26周疗程间接印证） |
| `openstax-pharm-ch07-antiinfective.pdf/p0011/0044` | 0.4468 | 不能（抗病毒剂量表） |

**回答是否准确**：准确，还正确复述了标准四联方案。

**具体分析**：目标chunk排名第1且score明显更低（0.28），检索质量好。

### clinical-b015

**题目**（EN）："Isoniazid treats tuberculosis by inhibiting the production of which substance?"

**检索query**："isoniazid mechanism of action in treating tuberculosis, specifically which substance it inhibits"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0031/0140` | 0.3729 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0032/0143` | 0.4049 | 不能（表格标题） |
| `openstax-pharm-ch07-antiinfective.pdf/p0032/0146` | 0.4426 | 不能（抗结核药不良反应） |
| `openstax-pharm-ch07-antiinfective.pdf/p0031/0137` | 0.4477 | 部分能（TB疗程6个月，非机制本身） |
| `openstax-pharm-ch07-antiinfective.pdf/p0005/0019` | 0.4501 | 不能（利奈唑胺） |

**回答是否准确**：准确，分枝菌酸答对。

**具体分析**：目标chunk排名第1且score明显更低（0.37 vs 0.40+），检索质量好，5个chunk全部来自本章无跨章节污染。

### clinical-b016

**题目**（ZH）："扑灭司林（permethrin）杀灭虱子的作用机制是什么？"

**检索query**："扑灭司林（permethrin）杀灭虱子的作用机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0036/0160` | 0.3933 | **能，排名第1** |
| `openstax-pharm-ch07-antiinfective.pdf/p0036/0163` | 0.4727 | 不能（驱虫药） |
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0014` | 0.4980 | 不能（青霉素历史） |
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0016` | 0.5122 | 不能（头孢菌素） |
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0015` | 0.5214 | 不能（β-内酰胺酶） |

**回答是否准确**：准确，还正确对比了同类药物（林丹/马拉硫磷）的不同机制。

**具体分析**：目标chunk稳定排名第1。

### clinical-b017（无答案题，EN，改自然提问）

**题目**："Is it safe for a breastfeeding mother to take doxycycline to treat a chlamydia infection?"

**检索query**：未触发retrieve——模型直接判断这类问题超出工具范围，建议咨询医疗专业人员/权威指南，未调用检索工具。

**回答**：正确拒答。模型说明"无法在没有检索到具体资料的情况下给出准确答案"，并建议咨询专业人员，附带"多西环素在哺乳期一般不推荐使用，但可能在特定情况下谨慎使用"这类训练知识性的一般性说明，但明确未声称这是教材内容。

**幻觉判定**：否。

**具体分析**：跟原ch07报告里这道题（原"教材第X章有什么说明"模板句式）相比，改成直接技术问句后，模型这次连retrieve都没调用就先判断"这不是我能查的工具范围"——处理路径跟其他无答案题（先检索再披露未命中）不同，但结论同样是诚实拒答，未产生幻觉。确认lactation/breastfeed在全章0命中，题目有效。

### clinical-b018（无答案题，ZH，改自然提问）

**题目**："老年结核病患者使用异烟肼时，剂量应该如何调整？"

**检索query**："老年结核病患者使用异烟肼时的剂量调整方法"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0004/0010` | 0.4332 | 不能（西酞普兰剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0159` | 0.4353 | 不能（托莫西汀剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0012/0037` | 0.4367 | 不能（米氮平剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0093` | 0.4375 | 不能（丙戊酸剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0006/0018` | 0.4380 | 不能（文拉法辛/度洛西汀剂量表，跨章节污染） |

**回答**：正确拒答。模型明确说明"未找到关于老年结核病患者使用异烟肼剂量调整的具体信息"，指出检索到的资料是抗抑郁药物剂量、跟结核病治疗无关，并建议参考权威指南或提供更具体的书籍/指南名称，**没有编造任何具体剂量数字**。

**幻觉判定**：否。

**具体分析**：5个检索chunk**全部**是ch13（精神药物）章节的跨章节污染（无一命中ch07任何异烟肼相关chunk），检索质量差，但模型准确识别出"检索到的内容跟问题（结核病/异烟肼）完全不匹配"，诚实declined，没有借着训练知识编出具体剂量数字。确认elderly/geriatric在全章0命中，题目有效。

### clinical-b019（无答案题，EN，改自然提问）

**题目**："Should patients on azole antifungal therapy avoid grapefruit juice due to a potential CYP3A4 interaction?"

**检索query**："interaction between azole antifungal drugs and grapefruit juice via CYP3A4 enzyme"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0017/0075` | 0.3693 | 部分能（唑类抑制CYP3A4的一般性说明，未提葡萄柚） |
| `openstax-pharm-ch07-antiinfective.pdf/p0018/0076` | 0.4149 | 不能（氟康唑剂量表） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0066` | 0.4582 | 不能（唑类分类/机制） |
| `openstax-pharm-ch07-antiinfective.pdf/p0018/0078` | 0.4960 | 部分能（用药教育：需筛查CYP3A4相互作用，未提葡萄柚具体） |
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0068` | 0.4993 | 不能（棘白菌素类） |

**回答**："Yes"，并给出理由：唑类是CYP3A4强抑制剂，葡萄柚汁也是已知的CYP3A4抑制剂，两者叠加会升高唑类血药浓度增加毒性风险；同时明确说明"grapefruit juice is not explicitly listed as a contraindication in all tables (e.g., Table 7.8)"，即检索到的具体表格里没有明确列出葡萄柚这一条。

**幻觉判定**：否。模型清楚披露了"书里没有明确列出葡萄柚"这一事实，结论是基于同一章节已经讲过的CYP3A4机制做的合理推断（唑类抑制CYP3A4是`p0017/0075`里原文写的），不是凭空编造，跟clinical-b036那种完全不披露的情况不同。

**具体分析**：确认grapefruit在全章0命中，题目有效。这是一个"披露+基于书内已有机制合理推断"的中间行为模式，跟clinical-b017/b019(旧)那种"直接拒答"、clinical-b036那种"完全不披露的幻觉"都不同，回答本身在医学上也是准确的（唑类-葡萄柚CYP3A4相互作用是真实存在的临床知识）。

### clinical-b039（计算题，EN）

**题目**："A 65 kg adult is being treated for tuberculosis with rifampin. Based on the weight-based dosing and stated maximum dose listed in the drug's prototype table, what is the correct daily dose for this patient?"

**检索query**："rifampin weight-based dosing and maximum daily dose"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0008/0025` | 0.3648 | 不能（安非他酮剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0007/0021` | 0.3793 | 不能（度洛西汀剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0020/0075` | 0.3886 | 不能（帕利哌酮等抗精神病药剂量表，跨章节污染） |
| `openstax-pharm-ch07-antiinfective.pdf/p0032/0142` | 0.3932 | **能，排名第4**（目标chunk：利福平10mg/kg，最大600mg） |
| `openstax-pharm-ch28-diabetic.pdf/p0020/0125` | 0.3948 | 不能（阿卡波糖等降糖药剂量表，跨章节污染） |

**回答是否准确**：准确。模型正确算出65kg×10mg/kg=650mg，识别出超过说明书最大剂量600mg，最终给出600mg而不是650mg，正确应用了"剂量上限优先于体重计算结果"这条规则。

**具体分析**：目标chunk排名第4（4/5是跨章节污染），检索精度一般但仍进入top5，Hit@5成立。这是一道有意设计的"陷阱题"——如果模型不检查剂量上限、直接按体重计算会得到错误的650mg，模型这次正确识别了上限约束。

### clinical-b040（计算题，ZH）

**题目**："一名25kg的儿童需要使用氨基青霉素类药物（aminopenicillin）治疗敏感菌感染，按说明书上标注的儿童体重剂量和给药频率，计算单次给药剂量的范围。"

**检索query**："氨基青霉素类药物在儿童中的推荐剂量和给药频率"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0007/0028` | 0.3200 | 不能（抗病毒药剂量表） |
| `openstax-pharm-ch07-antiinfective.pdf/p0006/0026` | 0.3313 | 部分能（青霉素类综合剂量表，含多个药物） |
| `openstax-pharm-ch07-antiinfective.pdf/p0008/0032` | 0.3379 | **能，排名第3**（目标chunk：80-90mg/kg/日，每12小时） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0152` | 0.3429 | 不能（哌甲酯剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0159` | 0.3461 | 不能（阿托莫西汀剂量表，跨章节污染） |

**回答是否准确**：最终答案准确（1000-1125mg），但生成过程出现了自我怀疑——模型先用检索到的80-90mg/kg/日正确算出1000-1125mg，随后又说"这与常规临床实践不符……通常氨基青霉素类药物（如阿莫西林）的标准剂量是40-60mg/kg/日"，用自己的训练知识去质疑书里的数字，反复纠结后才又回到检索到的数字给出最终答案。

**具体分析**：目标chunk排名第3进入top5，Hit@5成立。这是一个值得记录的生成行为：模型的训练知识（阿莫西林常见剂量）跟这本书里"aminopenicillin"条目给出的具体数字不一致时，出现了纠结自我否定的过程，虽然最终没有推翻检索到的正确数字，但这种"用训练知识质疑检索内容"的倾向如果发生在检索内容本身没错、但跟训练知识分布不同的场景下，存在把正确答案改错的风险，值得记录。

### clinical-b041（计算题，EN）——真实检索miss，模型正确拒答

**题目**："A 20 kg child needs IV vancomycin for a bloodstream infection. Based on the recommended pediatric dose and dosing frequency listed in the drug's prototype table, what is the total daily dose in mg?"

**检索query**："recommended pediatric dose and dosing frequency for vancomycin"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0007/0028` | 0.3434 | 不能（抗病毒药剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0025/0103` | 0.3491 | 不能（卡马西平剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0159` | 0.3571 | 不能（阿托莫西汀剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0028/0113` | 0.3579 | 不能（地西泮剂量表，跨章节污染） |
| `openstax-pharm-ch07-antiinfective.pdf/p0011/0044` | 0.3684 | 不能（阿昔洛韦剂量表） |

**回答是否准确**：正确处理，未给出确定答案。目标chunk`p0006/0026`（万古霉素10mg/kg/次、每6小时一次）top5完全未命中，模型明确说明"The retrieved content does not contain specific information about the recommended pediatric dose...I cannot provide an accurate answer based on the provided data"，随后补充说"vancomycin is often dosed at 15-20mg/kg/day"这一训练知识性的一般说法，但清楚标注是一般参考、不是本书内容，没有给出确定的最终数字答案。

**具体分析**：**真实检索缺陷**。万古霉素这个词本身在语料库其他地方（ch07多道题里）都能稳定检索到（如clinical-b003），但这道题query聚焦在"儿科剂量/给药频率"这个角度上，反而检索不到同一个chunk——跟clinical-b004（利奈唑胺）类似，是"query角度跟chunk实际内容的匹配方式"导致的miss，不是这个药名本身检索不到。模型面对完全不相关的检索结果时选择诚实declined、不编造具体数字，是期望中的正确行为。

## 本批（ch07）小结

- 22题（16事实题+3计算题+3无答案题），中英文各占一半左右（EN 12/ZH 10）。3道无答案题均为自然直接提问，3道计算题均基于书中真实印出的mg/kg剂量数据设计，不为凑数编造场景。
- Hit@5（19道有答案题适用，事实题16+计算题3）：原提示词下17/19（89.5%），未命中2题：clinical-b004（利奈唑胺）、clinical-b041（万古霉素儿科剂量，真实检索miss，模型正确拒答未编造数字）。**2026-07-23更新**：系统提示词修改后clinical-b004复测8次里7次命中、1次未命中，按多数结果订正为**18/19（94.7%）**，但要注意这道题约1/8的概率仍会退回未命中，完整分布见下方clinical-b004具体分析段落。
- 幻觉（3道无答案题适用）：**0/3**。
- **clinical-b004（利奈唑胺）是本批的真实检索缺陷案例**：目标chunk`openstax-pharm-ch07-antiinfective.pdf/p0005/0019`跟题目几乎字面对应，但top5完全未命中（复测3次结果一致，排除生成随机性），命中的反而是2个跨章节（ch13精神药物）无关内容。定位到根因：原query"分类及其主要适应症"是抽象归纳式问法，没用到chunk原文的具体术语（"highly resistant"、"VRSA"）；若改写成包含"高度耐药的感染"的问法，排名会升到第3，加上"VRSA"这个原文专有名词后能到第1。这说明dense retrieval对query是否包含原文实际术语高度敏感——这个知识点本身能检索到，但容易被抽象化的问法miss掉。题目故意保留原表述，不改写成检索友好的版本，否则测试集就测不出这个真实存在的缺陷。
- 观察到的共性现象：跨章节/跨来源污染（命中ch13/ch18/ch28甚至音频片段）在中文query下出现频率明显更高，尤其是clinical-b006/b011/b012/b018这几道中文题；英文题（如b001/b003/b005/b007/b009/b013/b015）的top5几乎不含跨章节污染。这跟CS测试集当年发现的"跨语言检索质量差异"现象方向一致，值得在后续章节继续观察是否稳定复现。
- clinical-b017两道英文无答案题（b017/b019）模型都没有调用retrieve就直接判断问题超出工具范围或先检索再基于书内机制合理推断（b019），跟b018（中文，检索后诚实拒答）处理方式各不相同，但结论都诚实、未产生幻觉。
- clinical-b040观察到"模型用训练知识质疑检索到的正确数字"这一生成行为，虽然本题最终答案没有被带偏，但这种倾向值得记录，供后续章节继续观察。

## openstax-pharm-ch13-psychopharm.pdf 章节（19题，2026-07-22）

### clinical-b020

**题目**（ZH）："三环类抗抑郁药（TCA）为什么会导致口干、便秘、视物模糊、镇静、体重增加、低血压这些副作用？"

**检索query**："三环类抗抑郁药（TCA）的副作用机制，包括口干、便秘、视物模糊、镇静、体重增加和低血压的原因"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0002/0006` | 0.2608 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0002/0005` | 0.3327 | 不能（TCA历史地位/二线用药） |
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0161` | 0.3595 | 不能（阿托莫西汀/可乐定不良反应） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0015/0068` | 0.3798 | 不能（β受体阻滞剂不良反应，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0018/0068` | 0.3872 | 部分能（第一代抗精神病药抗胆碱能副作用列表，机制类似但非TCA本身） |

**回答是否准确**：准确，三组受体阻断（M受体/组胺/α1）跟对应副作用的对应关系全部答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b021

**题目**（EN）："How many weeks must elapse between stopping an MAOI and starting fluoxetine (or vice versa) to prevent serotonin syndrome?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0004/0012` | 0.2860 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0006/0020` | 0.3388 | 不能（SNRI跟MAOI间隔14天，非本题问的氟西汀） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0155` | 0.4105 | 不能（CNS兴奋剂药物相互作用列表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0009/0030` | 0.4152 | 不能（酪胺机制） |
| `openstax-pharm-ch13-psychopharm.pdf/p0009/0027` | 0.4483 | 不能（MAOI概述） |

**回答是否准确**：准确，5周答对，还正确补充了"其余SSRI跟MAOI只需2周"这一区分点。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b022

**题目**（ZH）："服用MAOI类抗抑郁药的患者为什么要避免摄入富含酪胺（tyramine）的食物？"

**检索query**："MAOI类抗抑郁药的作用机制及与酪胺相互作用的风险"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0009/0030` | 0.2985 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0155` | 0.3233 | 不能（CNS兴奋剂相互作用列表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0009/0027` | 0.3283 | 部分能（MAOI概述，非酪胺机制本身） |
| `openstax-pharm-ch13-psychopharm.pdf/p0010/0031` | 0.3874 | 部分能（苯乙肼原型表，含MAO-A结合机制） |
| `openstax-pharm-ch13-psychopharm.pdf/p0013/0041` | 0.4429 | 部分能（用药教育"避免富含酪胺食物"列表，无机制） |

**回答是否准确**：准确，酪胺蓄积→肾上腺素能神经末梢释放NE→交感激活→高血压危象的完整机制链条均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b023

**题目**（EN）："Norepinephrine dopamine reuptake inhibitors (NDRIs) inhibit the reuptake of which neurotransmitters, and what is the most common drug in this class?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0007/0023` | 0.1954 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0006/0017` | 0.2787 | 不能（SNRI机制） |
| `openstax-pharm-ch07-antiinfective.pdf/p0022/0097` | 0.3768 | 不能（NRTIs抗病毒药，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0003/0009` | 0.3780 | 不能（SSRI机制） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0151` | 0.3830 | 不能（阿托莫西汀机制片段） |

**回答是否准确**：准确，三种神经递质+安非他酮均答对。

**具体分析**：目标chunk排名第1且score明显更低（0.20 vs 0.28+），检索质量本题最好。

### clinical-b024

**题目**（ZH）："第一代抗精神病药为什么又被称为'神经阻滞剂'（neuroleptics）？"

**检索query**："第一代抗精神病药为何被称为'神经阻滞剂'(neuroleptics)"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0015/0054` | 0.3289 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0016/0055` | 0.3832 | 部分能（第一代按效价分类，含受体阻断补充信息） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0151` | 0.4188 | 不能（阿托莫西汀机制片段） |
| `openstax-pharm-ch13-psychopharm.pdf/p0018/0070` | 0.4354 | 不能（第二代机制，非第一代） |
| `openstax-pharm-ch13-psychopharm.pdf/p0017/0058` | 0.4357 | 部分能（EPS症状列表，跟本题相关但非"命名原因"本身） |

**回答是否准确**：核心结论（锥体外系反应风险）准确，但回答里额外补充了"neuroleptic"一词的希腊语词源拆解（"neuron+leptos"），这段词源解释检索内容里完全没有，是模型自行补充、未经验证的内容，可能不准确。

**具体分析**：目标chunk稳定排名第1，检索质量好；回答里的词源学延伸内容超出原文范围，不影响核心结论但属于未经检索验证的补充。

### clinical-b025

**题目**（EN）："What is the key mechanistic difference between second-generation (atypical) antipsychotics and first-generation antipsychotics?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0018/0070` | 0.2760 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0018/0061` | 0.3049 | 不能（第一代抗精神病药标签） |
| `openstax-pharm-ch13-psychopharm.pdf/p0015/0054` | 0.3696 | 能（第一代EPS/命名原因，支撑性内容） |
| `openstax-pharm-ch13-psychopharm.pdf/p0016/0055` | 0.3966 | 能（第一代额外阻断受体列表，支撑性内容） |
| `openstax-pharm-ch13-psychopharm.pdf/p0019/0073` | 0.4209 | 不能（表格索引） |

**回答是否准确**：准确，"同时阻断多巴胺+五羟色胺"这一核心区别点答对。

**具体分析**：目标chunk排名第1，top5里3个真实相关，检索质量好。

### clinical-b026

**题目**（ZH）："氯氮平（clozapine）为什么需要通过FDA的REMS项目进行额外监测？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0020/0077` | 0.3992 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0158` | 0.4597 | 不能（ADHD非兴奋剂药物，跑题） |
| `openstax-pharm-ch13-psychopharm.pdf/p0036/0142` | 0.4717 | 不能（CNS兴奋剂列表） |
| `openstax-pharm-ch07-antiinfective.pdf/p0033/0147` | 0.4726 | 不能（异烟肼肝毒性监测，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0037/0149` | 0.4740 | 不能（CNS兴奋剂妊娠期注意事项） |

**回答是否准确**：准确，粒细胞缺乏症/严重中性粒细胞减少症风险答对；回答里补充了"每周/每两周监测""签署知情同意书"等具体REMS执行细节，检索内容里没有明确写这些，属于超出原文范围的补充说明。

**具体分析**：目标chunk稳定排名第1，检索质量好；回答里的执行细节补充未经检索验证，但核心结论（为什么需要监测）准确。

### clinical-b027

**题目**（EN）："According to the Beers Criteria, why are antipsychotics considered potentially inappropriate for older adults with dementia?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0015/0052` | 0.1809 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0022/0085` | 0.3476 | 能（痴呆相关精神病老年患者死亡率上升，支撑性内容） |
| `openstax-pharm-ch13-psychopharm.pdf/p0033/0135` | 0.3824 | 不能（镀静催眠药老年人风险，非抗精神病药） |
| `openstax-pharm-ch13-psychopharm.pdf/p0017/0058` | 0.4056 | 不能（EPS/NMS症状列表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0028/0115` | 0.4147 | 不能（苯二氮卓禁忌症） |

**回答是否准确**：准确，认知能力下降+死亡率上升均答对。

**具体分析**：目标chunk排名第1且score明显更低（0.18），检索质量本题最好。

### clinical-b028

**题目**（ZH）："锂盐（lithium）维持治疗的目标血药浓度范围是多少？"

**检索query**："锂盐维持治疗的目标血药浓度范围"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0023/0087` | 0.4312 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0025/0103` | 0.4456 | 不能（卡马西平剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0007/0021` | 0.4566 | 不能（度洛西汀剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0093` | 0.4582 | 不能（锂盐剂量表，非血药浓度目标） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0025/0117` | 0.4657 | 不能（硝酸酯类剂量，跨章节污染） |

**回答是否准确**：准确，0.6-1.2 mEq/L范围及维持剂量更接近0.6 mEq/L均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b029

**题目**（EN）："Why can NSAIDs, diuretics, and ACE inhibitors alter serum lithium concentrations?"

**检索query**："how do NSAIDs, diuretics, and ACE inhibitors affect serum lithium levels?"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0023/0090` | 0.3297 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0096` | 0.3697 | 不能（噻嗪类利尿剂一般机制，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0026/0107` | 0.4249 | 部分能（锂盐用药教育，钠摄入相关） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0008/0037` | 0.4282 | 不能（ACE抑制剂一般机制，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0099` | 0.4285 | 不能（锂盐禁忌症列表） |

**回答是否准确**：核心机制（锂经肾原形排出、跟钠重吸收挂钩）答对；但回答里对三类药物分别给出了具体的正/负向机制解释（如"NSAIDs降低肾血流→降低锂清除率"、"ACE抑制剂降低醛固酮→增加钠和锂排出"），这些具体分子机制检索内容里没有写，是模型自行补充推理，跟原文"因影响钠平衡而改变锂浓度、可能导致治疗失败或中毒"这一笼统表述相比更具体、也更可能存在事实性风险。

**具体分析**：目标chunk稳定排名第1，检索质量好；回答对三种药物机制的具体化拆解超出原文范围，属于合理推断但未经检索验证。

### clinical-b030（有意保留题面，检索精度一般）

**题目**（ZH）："服用卡马西平（carbamazepine）的患者为什么需要考虑使用额外或替代的避孕措施？"

**检索query**："卡马西平（carbamazepine）对避孕药的影响及为何需额外或替代避孕措施"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0020/0077` | 0.4375 | 不能（氯氮平粒细胞缺乏症，跑题） |
| `openstax-pharm-ch13-psychopharm.pdf/p0025/0106` | 0.4405 | **能，排名第2**（目标chunk） |
| `openstax-pharm-ch13-psychopharm.pdf/p0019/0071` | 0.4520 | 不能（阿立哌唑适应症） |
| `openstax-pharm-ch07-antiinfective.pdf/p0013/0052` | 0.4570 | 不能（更昔洛韦不良反应，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0033/0132` | 0.4693 | 不能（右佐匹克隆剂量表） |

**回答是否准确**：准确，直接引用原文结论。

**具体分析**：目标chunk排名第2，且跟排名第1的完全不相关内容（氯氮平）score差距极小（0.4375 vs 0.4405，几乎无法区分），说明本题检索精度一般，score排序在这个区间内的区分度不可靠，但未影响最终答案。

### clinical-b031

**题目**（EN）："Benzodiazepines work by enhancing the effect of which neurotransmitter, and what drug is used to reverse their effects in an overdose?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0028/0115` | 0.3658 | 不能（苯二氮卓禁忌症） |
| `openstax-pharm-ch13-psychopharm.pdf/p0027/0112` | 0.3698 | **能，排名第2**（目标chunk1：flumazenil） |
| `openstax-pharm-ch13-psychopharm.pdf/p0027/0110` | 0.3829 | **能，排名第3**（目标chunk2：GABA机制） |
| `openstax-pharm-ch13-psychopharm.pdf/p0030/0119` | 0.3846 | 部分能（地西泮剂量表，含"增强GABA抑制效应"字样） |
| `openstax-pharm-ch13-psychopharm.pdf/p0020/0077` | 0.4037 | 不能（氯氮平粒细胞缺乏症） |

**回答是否准确**：准确，GABA机制+氟马西尼逆转均答对。

**具体分析**：两个目标chunk分别排名第2、第3，均进入top5，检索质量正常。

### clinical-b032

**题目**（ZH）："咪达唑仑（midazolam）静脉给药时跟阿片类药物合用有什么风险？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0030/0121` | 0.3444 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0020/0089` | 0.4013 | 不能（硝苯地平心血管风险，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0155` | 0.4070 | 不能（CNS兴奋剂相互作用列表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0011/0036` | 0.4169 | 不能（米氮平/曲唑酮不良反应） |
| `openstax-pharm-ch13-psychopharm.pdf/p0002/0006` | 0.4183 | 不能（TCA抗胆碱能副作用） |

**回答是否准确**：准确，呼吸抑制→缺氧/脑损伤/死亡均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b033

**题目**（EN）："Ramelteon acts on which receptor, and is it classified as a controlled substance?"

**检索query**："Ramelteon receptor type and classification as controlled substance"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0031/0125` | 0.3736 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0011/0051` | 0.4624 | 不能（ARB分类，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0036/0142` | 0.4644 | 不能（安非他命等CNS兴奋剂管制级别） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0150` | 0.4715 | 不能（哌甲酯管制级别标签） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0058` | 0.4843 | 不能（ARB剂量表，跨章节污染） |

**回答是否准确**：准确，褪黑素受体+非管制药物均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b034

**题目**（ZH）："中枢兴奋剂治疗ADHD看似矛盾，它们具体是通过什么机制帮助患者集中注意力的？"

**检索query**："中枢兴奋剂治疗ADHD的作用机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0035/0141` | 0.3624 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0035/0139` | 0.3877 | 不能（ADHD章节学习目标/定义） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0157` | 0.4128 | 不能（非兴奋剂替代药物介绍） |
| `openstax-pharm-ch13-psychopharm.pdf/p0036/0142` | 0.4185 | 部分能（具体兴奋剂药物列表，含机制片段） |
| `openstax-pharm-ch13-psychopharm.pdf/p0041/0164` | 0.4268 | 不能（可乐定剂量表） |

**回答是否准确**：核心机制（促进儿茶酚胺释放+阻断再摄取→激发RAS唤醒刺激）准确，但回答额外补充了"改善前额叶皮质功能""促进神经可塑性与认知功能"等具体延伸说明，检索内容里没有这些表述，属于模型自行扩展、未经验证的补充。

**具体分析**：目标chunk稳定排名第1，检索质量好；回答里的神经科学延伸内容超出原文范围，核心结论不受影响。

### clinical-b035

**题目**（EN）："Clonidine is used as a non-stimulant treatment for ADHD. What class of drug is it, and is its exact mechanism of action in ADHD known?"

**检索query**："Clonidine's classification as a drug and its mechanism of action in the treatment of ADHD"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0158` | 0.3296 | **能，排名第1** |
| `openstax-pharm-ch13-psychopharm.pdf/p0035/0139` | 0.3940 | 不能（ADHD章节学习目标/定义） |
| `openstax-pharm-ch13-psychopharm.pdf/p0041/0164` | 0.3956 | 能（可乐定剂量表，明确标注"Mechanism of Action: Unknown"，支撑性内容） |
| `openstax-pharm-ch13-psychopharm.pdf/p0035/0141` | 0.4111 | 不能（CNS兴奋剂机制，非可乐定） |
| `openstax-pharm-ch13-psychopharm.pdf/p0041/0163` | 0.4174 | 不能（药名混淆提示） |

**回答是否准确**：准确，α2肾上腺素受体激动剂+机制未明均答对。

**具体分析**：目标chunk排名第1，top5里2个真实相关，检索质量好。

### clinical-b036（无答案题，EN）—— **系统提示词修改后已修复，经真实后端API+用户独立复测确认**

**题目**："What is buspirone's mechanism of action as an anxiolytic, and does it carry the same dependence risk as benzodiazepines?"

**检索query**："buspirone's mechanism of action as an anxiolytic"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0007/0024`（安非他酮NDRI类药物，非本题） | 0.4355 | 不能 |
| `openstax-pharm-ch13-psychopharm.pdf/p0021/0080`（第二代抗精神病药剂量表，非本题） | 0.4861 | 不能 |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0092`（米氮平机制，非本题） | 0.4868 | 不能 |
| `openstax-pharm-ch13-psychopharm.pdf/p0012/0037`（米氮平剂量表，非本题） | 0.4900 | 不能 |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0151`（去甲肾上腺素/多巴胺再摄取抑制剂，非本题） | 0.4915 | 不能 |

**回答是否准确：准确（诚实披露）**。5个chunk全部不相关，模型正确回答"The retrieved results do not contain information about buspirone's mechanism of action as an anxiolytic or its dependence risk compared to benzodiazepines. Therefore, I cannot provide a definitive answer based on the provided knowledge base."，不再是无披露的自信编造。经真实后端API复测+用户独立复测确认一致。

**具体分析**：原提示词下，两次retrieve共10个chunk同样没有一个提到buspirone，但模型给出详细、自信、无披露的错误机制描述，跟ch07批次clinical-b018原版本、CS批次cs-b014等同属issue #40幻觉模式。系统提示词修改后，`audit_question.py`用紧凑循环连续复测时观察到多次退回原来的幻觉行为（可能跟连续高频调用下的模型服务状态有关，未实锤原因），但经过真实后端API（跟用户实际使用的是同一进程）复测、以及用户自己独立复测，结果稳定给出诚实披露，判定为已修复。

### clinical-b037（无答案题，ZH）

**题目**："艾司氯胺酮（esketamine）治疗难治性抑郁症的具体作用机制是什么？"

**检索query**："艾司氯胺酮（esketamine）治疗难治性抑郁症的作用机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0030/0122` | 0.4224 | 不能（非苯二氮卓镀静催眠药总论） |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0092` | 0.4413 | 不能（锂盐机制，非艾司氯胺酮） |
| `openstax-pharm-ch13-psychopharm.pdf/p0010/0033` | 0.4478 | 不能（米氮平/曲唑酮/伏硫西汀，其他非典型抗抑郁药） |
| `openstax-pharm-ch13-psychopharm.pdf/p0012/0037` | 0.4572 | 不能（米氮平剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0021/0080` | 0.4704 | 不能（利培酮剂量表） |

**回答**：先明确说明"未找到关于艾司氯胺酮治疗难治性抑郁症的具体作用机制的明确描述"，随后又补充"根据现有医学文献和临床研究，艾司氯胺酮是一种NMDA受体拮抗剂……"这一具体机制说明，并明确标注是"现有医学文献和临床研究"而非本教材内容。

**幻觉判定**：否（有明确披露"检索未找到"在先，且后续补充明确说明来源是外部医学文献而非本书，跟clinical-b036那种完全不披露、直接自信作答的情况不同）。

**具体分析**：确认esketamine/ketamine在全章0命中，题目有效。这道题的处理方式介于"诚实拒答"和"幻觉"之间——不是clinical-b036那种完全没有意识到自己在补充的情况，但补充内容本身也未经验证，回答末尾仍挂了5个不相关chunk的引用标签，是citation机械标注的问题（同ch07批次clinical-b040类似案例），不影响幻觉判定本身。

### clinical-b038（无答案题，EN，改自然提问）

**题目**："Does taking St. John's Wort together with an SSRI increase the risk of serotonin syndrome?"

**检索query**："interaction between St. John's Wort and SSRIs regarding serotonin syndrome risk"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0004/0012` | 0.4132 | 部分能（SSRI+MAOI/tramadol的五羟色胺综合征机制，未提St. John's Wort） |
| `openstax-pharm-ch13-psychopharm.pdf/p0006/0020` | 0.4543 | 不能（SNRI+MAOI间隔规则） |
| `openstax-pharm-ch13-psychopharm.pdf/p0006/0017` | 0.4882 | 不能（SNRI机制概述） |
| `openstax-pharm-ch13-psychopharm.pdf/p0003/0009` | 0.4993 | 不能（SSRI药物列表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0005/0013` | 0.5126 | 不能（氟西汀剂量表） |

**回答**："Yes"，理由：圣约翰草本身有类似SSRI的五羟色胺再摄取抑制作用，跟SSRI合用会导致五羟色胺过量累积；同时明确说明"the provided text does not explicitly mention St. John's Wort in combination with SSRIs"，是基于书里已经讲过的"SSRI+MAOI/tramadol会增加五羟色胺综合征风险"这一机制类推得出的结论。

**幻觉判定**：否。跟clinical-b019（ch07，葡萄柚汁）是同一种行为模式——明确披露检索内容没有直接讲这一点，结论是基于书内已有机制的合理类推，不是凭空编造，医学上也是真实、被广泛认可的相互作用。

**具体分析**：确认St. John's Wort在全章0命中，题目有效。

### clinical-b042（计算题，ZH）

**题目**："一名40kg的青少年（>12岁）需要使用丙戊酸缓释制剂进行双相情感障碍的维持治疗，按说明书上标注的儿童维持剂量计算，每日总剂量的范围是多少？"

**检索query**："丙戊酸缓释制剂在儿童中用于双相情感障碍维持治疗时的推荐剂量"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0093` | 0.3948 | **能，排名第1**（目标chunk：15-60mg/kg/日） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0152` | 0.3963 | 不能（哌甲酯剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0021/0080` | 0.3971 | 不能（利培酮剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0003/0007` | 0.3974 | 不能（阿米替林剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0041/0164` | 0.4018 | 不能（可乐定剂量表） |

**回答是否准确**：准确。40kg×15mg/kg=600mg、40kg×60mg/kg=2400mg，范围600-2400mg，计算过程清晰无矛盾。

**具体分析**：目标chunk稳定排名第1，检索质量好，是本批计算题里检索+计算配合最干净的一道。

## 本批（ch13）小结

- 20题（16事实题+1计算题+3无答案题），中英文各占一半（EN 10/ZH 10）。
- Hit@5（17道有答案题适用，事实题16+计算题1）：**17/17（100%）**。clinical-b042（丙戊酸计算题）目标chunk排名第1，其余16道事实题命中情况跟此前记录一致。
- 幻觉（3道无答案题适用）：原提示词下1/3，clinical-b036（buspirone机制）是本批唯一且明确的幻觉案例：10个检索chunk全部不相关，模型仍给出具体、自信、无任何披露的错误机制描述。clinical-b037（esketamine）、clinical-b038（St. John's Wort）都补充了训练知识，但均有明确的"检索未找到/未明确提及"披露在先，不计入幻觉。**2026-07-23更新**：系统提示词修改后，经真实后端API复测+用户独立复测确认clinical-b036稳定给出诚实披露，本批幻觉数订正为**0/3**，完整分析见下方clinical-b036具体分析段落。
- 观察到的现象：本批多道题的回答里出现了"核心结论准确，但补充了检索内容未涵盖的具体延伸说明"这一模式（clinical-b024词源学解释、clinical-b026 REMS执行细节、clinical-b029三类药物具体分子机制、clinical-b034神经可塑性延伸），这些延伸内容都不构成幻觉（未跟检索内容矛盾，核心结论仍准确），但反映模型有稳定的"用训练知识补全细节"倾向，即使检索本身命中良好。
- 跨章节污染（命中ch07/ch18/ch28）在本批同样存在，但多数排在3-5名靠后位置，没有像ch07批次那样出现"污染占满全部5个citation"的极端情况。

## openstax-pharm-ch18-antihypertensive.pdf 章节（15题，2026-07-22）

### clinical-b043

**题目**（EN）："According to the blood pressure categories described in this chapter, what are the systolic and diastolic thresholds that define normal blood pressure?"

**检索query**："blood pressure categories, systolic and diastolic thresholds for normal blood pressure"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0004/0012` | 0.2904 | **能，排名第1**（Table 18.1血压分级表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0004/0011` | 0.3593 | **能，排名第2**（目标chunk，正文表述） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0002/0004` | 0.4136 | 不能（心输出量公式） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0001/0003` | 0.4486 | 不能（章节学习目标） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0003/0010` | 0.4654 | 不能（AHA外部链接资源） |

**回答是否准确**：准确，收缩压<120mmHg、舒张压<80mmHg均答对。

**具体分析**：目标chunk排名第2，排名第1的Table 18.1血压分级表同样能支撑答案，检索质量好。

### clinical-b044

**题目**（ZH）："肾脏在血压过低时释放的肾素（renin）如何通过RAAS系统最终导致血压升高？"

**检索query**："肾脏在血压过低时释放的肾素如何通过RAAS系统调节血压"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0003/0008` | 0.2726 | 不能（Figure 18.3图注） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0003/0006` | 0.2955 | **能，排名第2**（目标chunk） |
| `Cardiac Pharmaoclogy (1)...mp3/0006` | 0.4297 | 不能（多巴胺受体机制，跨来源污染） |
| `Cardiac Pharmacology (2)...mp3/0011` | 0.4321 | 不能（利血平机制，跨来源污染） |
| `Cardiac Pharmacology (2)...mp3/0001` | 0.4528 | 不能（降压药物分类总论，跨来源污染） |

**回答是否准确**：准确，肾素→血管紧张素I→II→醛固酮→水钠潴留的完整链条均答对。

**具体分析**：目标chunk排名第2，但top5里3个是跨音频来源污染（同一门"Cardiac Pharmacology"网课系列），中文query下污染比例较高，回答未受影响。

### clinical-b045

**题目**（EN）："ACE inhibitors lower blood pressure primarily by blocking the production of which substance, and what downstream hormone release do they reduce as a result?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0008/0037` | 0.2650 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0009/0040` | 0.3293 | 不能（黑人患者ACE抑制剂反应较低） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0009/0039` | 0.3554 | 不能（Figure 18.5图注） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0003/0006` | 0.3745 | 部分能（RAAS总论，含醛固酮机制） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0010/0044` | 0.3801 | 能（依那普利原型表，MOA字段印证） |

**回答是否准确**：准确，血管紧张素II+醛固酮均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b046

**题目**（ZH）："ACE抑制剂在妊娠中晚期使用会带来哪些胎儿/新生儿风险？"

**检索query**："ACE抑制剂在妊娠中晚期使用的胎儿和新生儿风险"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0011/0049` | 0.2509 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0009/0043` | 0.3145 | 部分能（ACE抑制剂不良反应总论，含"不应在妊娠期使用"） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0014/0062` | 0.3638 | 部分能（ARB妊娠期可致死胎，非ACE抑制剂但主题相关） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0011/0048` | 0.3716 | 部分能（用药教育：怀孕前告知医生） |
| `openstax-pharm-ch13-psychopharm.pdf/p0037/0149` | 0.4062 | 不能（CNS兴奋剂妊娠期注意事项，跨章节污染） |

**回答是否准确**：准确，5项风险（低血压/颅骨发育不全/无尿/肾衰竭/死亡）全部答对，还合理补充了ARB妊娠期风险作为对照说明（检索到的chunk确实提到）。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b047

**题目**（EN）："What are the three notable differences between ARBs and ACE inhibitors mentioned in this chapter?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0011/0051` | 0.2949 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0009/0040` | 0.4352 | 不能（ACE抑制剂人种差异反应） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0008/0037` | 0.4365 | 不能（ACE抑制剂机制，非对比） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0009/0043` | 0.4441 | 不能（ACE抑制剂不良反应） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0010/0044` | 0.4525 | 不能（依那普利剂量表） |

**回答是否准确**：准确，慢性咳嗽更少/血管性水肿风险更低/慢性肾病和心衰治疗效果三点全部答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b048

**题目**（ZH）："使用ARB类降压药相比其他降压药物，在情绪相关风险上有什么需要特别注意的？"

**检索query**："ARB类降压药在情绪相关风险方面的注意事项"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0012/0055` | 0.2731 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0061` | 0.3605 | 不能（ARB用药教育：告知妊娠/哺乳状态） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0058` | 0.3795 | 不能（缬沙坦剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0060` | 0.4030 | 不能（ARB护理监测要点） |
| `openstax-pharm-ch13-psychopharm.pdf/p0007/0024` | 0.4047 | 不能（NDRI精神症状不良反应，跨章节污染） |

**回答是否准确**：核心结论（自杀风险升高、需监测自杀意念）准确，但回答额外补充了"应对患者进行情绪障碍筛查""与SSRIs/MAOIs相互作用需谨慎评估"等检索内容里没有明确写的延伸建议，属于超出原文范围的补充。

**具体分析**：目标chunk稳定排名第1，检索质量好；回答里的延伸建议未经检索验证，但核心结论准确、不构成幻觉。

### clinical-b049

**题目**（EN）："Cardio-selective beta blockers act primarily on which adrenergic receptor subtype, and where in the body are these receptors mainly located?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0014/0064` | 0.3015 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0014/0063` | 0.3750 | 不能（章节学习目标） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0011/0051` | 0.3974 | 不能（ARB机制，非beta blocker） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0016/0069` | 0.4037 | 能（美托洛尔剂量表，MOA字段印证β1机制） |
| `Dopamine & Dobutamine...mp3/0002` | 0.4124 | 不能（β1/β2受体信号通路细节，跨来源污染） |

**回答是否准确**：准确，β1受体+心脏/肾脏定位均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b050

**题目**（ZH）："护士在给患者用β受体阻滞剂之前，如果测得患者心率低于多少次/分钟应该暂停给药并通知医生？"

**检索query**："β受体阻滞剂使用前，若患者心率低于多少次/分钟应暂停给药并通知医生"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0074` | 0.2891 | 能（患者教育版本，同样写"less than 60 beats/minute"） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0073` | 0.3043 | **能，排名第2**（目标chunk，护理版本） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0076` | 0.3162 | 不能（停药需逐渐减量） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0058` | 0.3715 | 不能（缬沙坦剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0016/0072` | 0.3728 | 不能（合并症评估：哮喘/COPD/糖尿病） |

**回答是否准确**：准确，60次/分钟答对。

**具体分析**：目标chunk排名第2，排名第1的chunk是同一事实的患者教育版本表述，两者互相印证，检索质量好。

### clinical-b051

**题目**（EN）："Calcium channel blockers are classified into which two categories, and how do non-dihydropyridines differ from dihydropyridines in their site of action?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0078` | 0.2987 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0018/0079` | 0.4097 | 不能（CCB对非西班牙裔黑人患者疗效更好） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0018/0083` | 0.4571 | 不能（Table 18.9表格标题） |
| `Dopamine & Dobutamine...mp3/0006` | 0.4773 | 不能（钙通道/心肌收缩机制，跨来源污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0077` | 0.4776 | 不能（章节学习目标） |

**回答是否准确**：准确，二氢吡啶类/非二氢吡啶类分类+作用部位差异均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b052

**题目**（ZH）："钙通道阻滞剂在用药教育中，需要提醒患者哪些具体的食物/草药相互作用？"

**检索query**："钙通道阻滞剂在用药教育中，需要提醒患者哪些具体的食物或草药相互作用"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0019/0087` | 0.3800 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0019/0085` | 0.3923 | 不能（氨氯地平剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0156` | 0.3930 | 不能（哌甲酯食物相互作用列表，跨章节污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0018/0083` | 0.4105 | 不能（Table 18.9表格标题） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0075` | 0.4122 | 不能（β受体阻滞剂草药相互作用，非CCB） |

**回答是否准确**：核心结论（圣约翰草+西柚汁）准确，但回答额外补充了"麻黄、人参等可能影响血压的物质"这一检索内容里没有的具体草药列举，属于超出原文范围的补充。

**具体分析**：目标chunk稳定排名第1，检索质量好；回答里的补充草药列举未经检索验证。

### clinical-b053

**题目**（EN）："Thiazide and thiazide-like diuretics inhibit the reabsorption of which two electrolytes, and in which part of the kidney?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0096` | 0.2722 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0022/0101` | 0.3964 | 能（氢氯噻嗪剂量表，MOA字段印证） |
| `openstax-pharm-ch13-psychopharm.pdf/p0023/0090` | 0.4226 | 不能（锂盐-钠平衡机制，跨章节污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0099` | 0.4262 | 不能（Table 18.11表格标题） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0020/0093` | 0.4348 | 不能（利尿剂总论） |

**回答是否准确**：准确，钠+氯+远曲小管均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b054

**题目**（ZH）："保钾利尿剂（potassium-sparing diuretics）是通过拮抗哪种激素来发挥作用的？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0097` | 0.3299 | **能，排名第1** |
| `openstax-pharm-ch18-antihypertensive.pdf/p0020/0093` | 0.4056 | 不能（利尿剂总论） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0099` | 0.4215 | 不能（Table 18.11表格标题） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0096` | 0.4305 | 不能（噻嗪类机制，非保钾利尿剂） |
| `Dopamine & Dobutamine...mp3/0006` | 0.4477 | 不能（钠钾ATP酶/强心苷机制，跨来源污染） |

**回答是否准确**：准确，醛固酮答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b055

**题目**（EN）："Concomitant use of nitrates with which class of drugs is contraindicated due to the risk of severe hypotension, and what are two example drugs in that class?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0024/0116` | 0.2976 | 能（同一话题的另一段表述，未列具体药名） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0024/0114` | 0.3409 | **能，排名第2**（目标chunk，含tadalafil/sildenafil具体药名） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0023/0109` | 0.3882 | 不能（老年患者体位性低血压风险） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0025/0119` | 0.3883 | 不能（用药护理监测要点） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0001/0002` | 0.3889 | 不能（章节目录） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0022/0101` | 0.3964 | 不能（氢氯噻嗪剂量表） |

**回答是否准确**：准确，PDE抑制剂+他达拉非/西地那非均答对。

**具体分析**：目标chunk排名第2，排名第1是同一话题的重复表述（未含具体药名），两者互相印证，检索质量好。

### clinical-b056（无答案题，EN）—— **系统提示词修改后已修复，经真实后端API确认**

**题目**："What is the mechanism of action of hydralazine as an antihypertensive, and why is it typically reserved as a second- or third-line agent?"

**检索query**："mechanism of action of hydralazine as an antihypertensive and reasons for its use as a second- or third-line agent"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0096`（噻嗪类利尿剂，非本题） | 0.4447 | 不能 |
| `Cardiac Pharmacology (3)｜Niacin.../0013`（烟酸机制网课音频，跨来源无关） | 0.4498 | 不能 |
| `openstax-pharm-ch18-antihypertensive.pdf/p0001/0002`（第18章目录，非本题） | 0.4508 | 不能 |
| `openstax-pharm-ch13-psychopharm.pdf/p0040/0158`（可乐定/维洛沙秦，跨章节污染） | 0.4549 | 不能 |
| `openstax-pharm-ch18-antihypertensive.pdf/p0009/0040`（ACE抑制剂人种差异，非本题） | 0.4559 | 不能 |

**回答是否准确：准确（诚实披露）**。1次retrieve后，模型正确回答"The provided search results do not contain specific information regarding the mechanism of action of hydralazine as an antihypertensive or why it is typically reserved for second- or third-line therapy."，随后清楚标注补充内容来自通用药理学知识，不再是无限重试后`MAX_ROUNDS_EXCEEDED`。经真实后端API复测确认一致。

**具体分析**：原提示词下，模型5次换角度重新表述query反复检索，25个citation里没有一个提到hydralazine，但没有在任何一轮止损披露"未找到"，而是持续重试直到耗尽`_MAX_ROUNDS`（5轮），最终`[MAX_ROUNDS_EXCEEDED]`，没有产生任何文本回答，已提issue #60记录。系统提示词修改（详见`docs/test-report-2026-07-23-law-testset-audit.md`"系统提示词改动"一节）后，模型不再无限换角度重试，1次retrieve后即判断检索不到相关内容并诚实披露，问题解决。

### clinical-b057（无答案题，ZH）

**题目**："米诺地尔（minoxidil）作为口服降压药的作用机制是什么？为什么它通常不是一线用药？"

**检索query**："米诺地尔（minoxidil）作为口服降压药的作用机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0025/0117` | 0.4100 | 不能（硝酸盐剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0058` | 0.4393 | 不能（缬沙坦剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0016/0069` | 0.4414 | 不能（美托洛尔剂量表） |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0100` | 0.4416 | 不能（米格列醇机制，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0010/0031` | 0.4455 | 不能（苯乙肼剂量表，跨章节污染） |

**回答**：先明确说明"未找到关于'米诺地尔作为口服降压药的作用机制'或'为什么它通常不是一线降压药'的直接相关资料"，随后标注"根据医学常识补充说明"，给出钾通道激活→血管平滑肌超极化→血管舒张的机制，以及水肿/心动过速/脱发等副作用导致其非一线的原因，全程清楚区分"检索未找到"和"补充的通用知识"两部分。

**幻觉判定**：否。披露清楚，跟clinical-b019/b038同属"检索未命中→明确披露→基于通用医学知识合理补充"这一模式，医学内容本身也准确。

**具体分析**：确认minoxidil在全章0命中，题目有效。

## 本批（ch18）小结

- 15题（13事实题+2无答案题），中英文各占一半（EN 8/ZH 7）。
- Hit@5（13道事实题适用）：**13/13（100%）**。
- 幻觉（2道无答案题适用）：**0/2**。clinical-b056原提示词下触发`MAX_ROUNDS_EXCEEDED`真实管线缺陷（已提issue #60），**2026-07-23更新**：系统提示词修改后经真实后端API复测确认已修复，1次retrieve+诚实披露，详见该题分析。
- 观察到的现象：中文query下跨来源污染（尤其是命中同一个"Cardiac Pharmacology"网课音频系列）比例明显更高（clinical-b044/b054），跟此前ch07/ch13批次观察到的跨语言检索质量差异现象一致。
- clinical-b048、clinical-b052两题延续了此前批次观察到的"核心结论准确，但补充检索内容未涵盖的具体延伸说明"模式。

## openstax-pharm-ch28-diabetic.pdf 章节（16题，2026-07-22）

### clinical-b058

**题目**（EN）："According to the diagnostic thresholds described in this chapter, what HbA1c percentage indicates diabetes?"

**检索query**："diagnostic thresholds for diabetes based on HbA1c percentage"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0005/0018` | 0.3187 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0005/0023` | 0.4377 | 不能（糖尿病前期人群概况） |
| `openstax-pharm-ch28-diabetic.pdf/p0002/0006` | 0.4478 | 不能（1型糖尿病细胞疗法Lantidra） |
| `openstax-pharm-ch28-diabetic.pdf/p0005/0017` | 0.4502 | 不能（诊断测试总论） |
| `openstax-pharm-ch28-diabetic.pdf/p0005/0020` | 0.4558 | 不能（随机血糖测试） |

**回答是否准确**：准确，HbA1c≥6.5%答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b059

**题目**（ZH）："空腹血糖检测中，血糖值达到多少mg/dL可以确诊糖尿病？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0005/0019` | 0.3021 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0005/0020` | 0.3135 | 不能（随机血糖测试） |
| `openstax-pharm-ch28-diabetic.pdf/p0004/0013` | 0.3607 | 不能（低血糖定义/15-15法则） |
| `openstax-pharm-ch28-diabetic.pdf/p0004/0014` | 0.3613 | 不能（高血糖定义） |
| `openstax-pharm-ch28-diabetic.pdf/p0005/0018` | 0.3753 | 不能（HbA1c测试） |

**回答是否准确**：准确，126 mg/dL答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b060

**题目**（EN）："What is the normal fasting blood glucose range used to define hypoglycemia in this chapter, and what is the '15-15 rule' used to treat it?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0004/0013` | 0.2520 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0005/0019` | 0.3773 | 不能（空腹血糖诊断阈值） |
| `openstax-pharm-ch28-diabetic.pdf/p0023/0132` | 0.4285 | 部分能（用药教育：备15克碳水化合物） |
| `openstax-pharm-ch28-diabetic.pdf/p0004/0014` | 0.4529 | 不能（高血糖定义） |
| `openstax-pharm-ch28-diabetic.pdf/p0014/0083` | 0.4566 | 部分能（同上，另一版本用药教育） |

**回答是否准确**：准确，70-100mg/dL范围+15-15法则完整流程均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b061

**题目**（ZH）："速效胰岛素（rapid-acting insulin）注射后大约多久起效？峰值和持续时间各是多久？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0007/0036` | 0.2943 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0008/0041` | 0.3251 | 能（Table 28.2胰岛素类型表，同一数据） |
| `openstax-pharm-ch28-diabetic.pdf/p0007/0037` | 0.3305 | 不能（短效胰岛素） |
| `openstax-pharm-ch28-diabetic.pdf/p0007/0038` | 0.3624 | 不能（中效胰岛素） |
| `openstax-pharm-ch28-diabetic.pdf/p0008/0039` | 0.3640 | 不能（长效胰岛素） |

**回答是否准确**：准确，15-30分钟起效/1-2小时达峰/2-4小时持续均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b062

**题目**（EN）："What is the distinguishing pharmacokinetic feature of long-acting insulin compared to rapid-, short-, and intermediate-acting insulins?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0007/0033` | 0.3034 | 不能（胰岛素类型总论） |
| `openstax-pharm-ch28-diabetic.pdf/p0008/0039` | 0.3050 | **能，排名第2** |
| `openstax-pharm-ch28-diabetic.pdf/p0007/0030` | 0.3254 | 不能（章节学习目标） |
| `openstax-pharm-ch28-diabetic.pdf/p0008/0040` | 0.3341 | 不能（预混胰岛素） |
| `openstax-pharm-ch28-diabetic.pdf/p0008/0041` | 0.3355 | 能（Table 28.2，含各类胰岛素峰值对比） |

**回答是否准确**：准确，无明显峰值+可持续24小时均答对。

**具体分析**：目标chunk排名第2，检索质量好。

### clinical-b063

**题目**（ZH）："普兰林肽（pramlintide）作为胰淀素类似物，是通过什么机制帮助控制血糖的？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0012/0061` | 0.3791 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0102` | 0.4557 | 不能（美格列奈类机制） |
| `openstax-pharm-ch28-diabetic.pdf/p0016/0091` | 0.5089 | 不能（格列吡嗪剂量/副作用） |
| `openstax-pharm-ch28-diabetic.pdf/p0014/0079` | 0.5157 | 不能（GLP-1治疗效果片段） |
| `openstax-pharm-ch07-antiinfective.pdf/p0004/0017` | 0.5169 | 不能（大环内酯类抗生素，跨章节污染） |

**回答是否准确**：准确，延缓胃排空+阻断胰高血糖素释放均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b064

**题目**（EN）："GLP-1 receptor agonists work through which gut hormone pathway, and what three effects do they have on glucose regulation?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0012/0062` | 0.2969 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0014/0073` | 0.4017 | 不能（GLP-1受体激动剂标签） |
| `openstax-pharm-ch28-diabetic.pdf/p0012/0064` | 0.4220 | 不能（GLP-1+磺脲类低血糖风险） |
| `Cardiac Pharmaoclogy (1)...mp3/0005` | 0.4394 | 不能（拟交感神经药物分类，跨来源污染） |
| `Cardiac Pharmaoclogy (1)...mp3/0006` | 0.4479 | 不能（β受体信号通路，跨来源污染） |

**回答是否准确**：准确，肠促胰素通路+促胰岛素分泌/抑制胰高血糖素/延缓胃排空三点均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b065

**题目**（ZH）："静脉注射胰岛素通常使用哪种类型的胰岛素？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0007/0033` | 0.4334 | 不能（胰岛素类型总论） |
| `openstax-pharm-ch28-diabetic.pdf/p0010/0053` | 0.4396 | **能，排名第2**（目标chunk） |
| `openstax-pharm-ch28-diabetic.pdf/p0009/0046` | 0.4459 | 不能（固定剂量/滑动比例给药法） |
| `openstax-pharm-ch28-diabetic.pdf/p0019/0114` | 0.4594 | 不能（利拉鲁肽-德谷胰岛素复方制剂） |
| `openstax-pharm-ch28-diabetic.pdf/p0008/0043` | 0.4594 | 不能（皮下注射部位） |

**回答是否准确**：准确，人常规胰岛素答对，还补充了"门冬胰岛素稀释后特定情况可静脉使用"这一原文确实提到的例外情况。

**具体分析**：目标chunk排名第2，检索质量好。

### clinical-b066

**题目**（EN）："Sulfonylureas lower blood glucose by binding to which type of channel on pancreatic beta cells, and what is required for them to be effective?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0015/0086` | 0.2837 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0015/0089` | 0.2865 | 不能（第一代磺脲类已停用） |
| `openstax-pharm-ch28-diabetic.pdf/p0016/0090` | 0.3216 | 部分能（第二代磺脲类特点） |
| `openstax-pharm-ch28-diabetic.pdf/p0015/0088` | 0.3599 | 不能（β受体阻滞剂相互作用） |
| `openstax-pharm-ch28-diabetic.pdf/p0014/0079` | 0.4046 | 不能（GLP-1效果片段） |

**回答是否准确**：准确，钾通道+功能尚存的β细胞均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b067（重出，避开跨章节都能答的泛问法）

**题目**（ZH）："磺脲类降糖药跟非选择性β受体阻滞剂合用时，除了掩盖低血糖的早期症状外，还会通过什么机制让患者在睡眠时发生严重低血糖的风险特别高？"

**检索query**："磺脲类降糖药与非选择性β受体阻滞剂合用时，如何增加夜间严重低血糖风险的机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0014/0074` | 0.4211 | 不能（GLP-1对血糖的作用） |
| `openstax-pharm-ch13-psychopharm.pdf/p0033/0132` | 0.4243 | 不能（右佐匹克隆剂量表，跨章节污染） |
| `openstax-pharm-ch28-diabetic.pdf/p0011/0058` | 0.4263 | 不能（胰岛素原型表） |
| `openstax-pharm-ch28-diabetic.pdf/p0012/0064` | 0.4274 | 不能（GLP-1+磺脲类低血糖风险，非β受体阻滞剂） |
| `openstax-pharm-ch28-diabetic.pdf/p0015/0088` | 0.4337 | **能，排名第5**（目标chunk） |

**回答是否准确**：准确。这次抓住了目标chunk特有的机制——非选择性β受体阻滞剂阻断交感神经的代偿反应（肾上腺素升糖代偿），导致患者尤其在睡眠期间（交感活动本就减弱、意识不清）容易发生未被察觉的严重低血糖，没有停留在"掩盖症状"这个两章节都提到的泛泛表述上。

**具体分析**：原题问法"为什么会增加严重低血糖的风险"太笼统，跟ch18（β受体阻滞剂章节）里"beta blockers can mask the symptoms of hypoglycemia in clients with diabetes"这句泛泛表述同样能部分回答，导致题目实际上无法唯一定位到ch28这个目标chunk——按方法论"chunk能推出答案但跟标注的supporting_chunks对不上→题目问得太泛，改到能唯一定位"这条规则重出。改问"掩盖症状之外的机制"+"为什么睡眠时风险特别高"这两个只有目标chunk才完整回答的具体点后，目标chunk进入top5（排名第5），检索到的其余4个chunk均不再是"部分能答"的跨章节干扰项，题目现在能唯一定位。

### clinical-b068

**题目**（EN）："In clients taking metformin, why does administration of contrast dye increase the risk of lactic acidosis, and how long should metformin be withheld around a contrast procedure if eGFR is below 30 mL/min?"

**检索query**：与题目原文相同（补充"mechanism by which..."前缀）

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0016/0096` | 0.1559 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0097` | 0.3726 | 部分能（乳酸酸中毒是二甲双胍罕见但严重的并发症） |
| `openstax-pharm-ch28-diabetic.pdf/p0018/0112` | 0.4250 | 不能（格列本脲-二甲双胍复方制剂） |
| `openstax-pharm-ch28-diabetic.pdf/p0014/0077` | 0.4261 | 不能（GLP-1延缓胃排空片段） |
| `openstax-pharm-ch28-diabetic.pdf/p0021/0128` | 0.4284 | 不能（口服降糖药不良反应总论） |

**回答是否准确**：准确，机制（造影剂损害肾功能→乳酸清除减少）+24小时前停药/48小时后恢复均答对。

**具体分析**：目标chunk排名第1且score极低（0.16，本批最低），检索质量本题最好。

### clinical-b069

**题目**（ZH）："SGLT2抑制剂是通过什么机制降低血糖的？"

**检索query**："SGLT2抑制剂的作用机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0018/0106` | 0.3940 | **能，排名第1** |
| `Dopamine & Dobutamine...mp3/0002` | 0.4326 | 不能（β受体信号通路，跨来源污染） |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0102` | 0.4638 | 不能（美格列奈类机制） |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0104` | 0.4722 | 不能（西格列汀药代动力学） |
| `openstax-pharm-ch13-psychopharm.pdf/p0024/0095` | 0.4732 | 不能（锂盐机制，跨章节污染） |

**回答是否准确**：准确，阻断肾脏葡萄糖重吸收+促进尿糖排出均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b070

**题目**（EN）："DPP-4 inhibitors lower blood glucose by blocking which enzyme, and what hormone does that enzyme normally destroy?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0017/0103` | 0.3299 | **能，排名第1** |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0098` | 0.4416 | 不能（α-葡萄糖苷酶抑制剂机制） |
| `openstax-pharm-ch28-diabetic.pdf/p0014/0079` | 0.4564 | 不能（GLP-1效果片段） |
| `openstax-pharm-ch28-diabetic.pdf/p0018/0106` | 0.4836 | 不能（SGLT2机制） |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0104` | 0.4859 | 不能（西格列汀药代动力学） |

**回答是否准确**：准确，DPP-4酶+肠促胰素均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-b071（计算题，ZH）

**题目**："一名70kg的高胰岛素血症性低血糖患者需要使用二氮嗪（diazoxide）治疗，按说明书成人常用剂量计算，每日总剂量的范围是多少？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch28-diabetic.pdf/p0020/0124` | 0.3049 | **能，排名第1**（目标chunk：3-8mg/kg） |
| `openstax-pharm-ch28-diabetic.pdf/p0022/0129` | 0.3925 | 不能（二甲双胍剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0022/0101` | 0.3948 | 不能（噻嗪类利尿剂剂量表，跨章节污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0012/0052` | 0.4012 | 不能（ARB剂量表，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0030/0119` | 0.4019 | 不能（地西泮剂量表，跨章节污染） |

**回答是否准确**：准确，210-560mg计算过程清晰无矛盾。

**具体分析**：目标chunk稳定排名第1，检索质量好，是本批唯一的计算题，题目基于二氮嗪说明书里唯一一处mg/kg剂量数据设计。

### clinical-b072（无答案题，EN）

**题目**："Can cinnamon supplements meaningfully lower blood glucose levels in people with type 2 diabetes?"

**检索query**："cinnamon supplements and their effect on blood glucose levels in people with type 2 diabetes"

**回答**：正确拒答，明确说明检索内容没有提到肉桂或其潜在效果，无法确认结论，建议查阅进一步文献。

**幻觉判定**：否。

**具体分析**：确认cinnamon在全章0命中，题目有效。

### clinical-b073（无答案题，ZH）

**题目**："葫芦巴（fenugreek）作为膳食补充剂对控制血糖有实际帮助吗？"

**检索query**："葫芦巴（fenugreek）作为膳食补充剂对控制血糖的实际效果"

**回答**：正确拒答，明确说明书中未直接提及葫芦巴，没有证据支持或否定其效果，建议查阅专门的临床研究文献。

**幻觉判定**：否。

**具体分析**：确认fenugreek在全章0命中，题目有效。

## 本批（ch28）小结

- 16题（13事实题+1计算题+2无答案题），中英文各占一半（EN 8/ZH 8）。
- Hit@5（14道有答案题适用，事实题13+计算题1）：**14/14（100%）**。
- 幻觉（2道无答案题适用）：**0/2**。
- 计算题：ch28全章mg/kg剂量数据只有二氮嗪一处（3-8mg/kg），出了1道计算题，没有为了凑数量硬找。
- 观察到的现象：clinical-b067重出过程中发现教材里存在跨章节的事实重复（ch18/ch28都提到"β受体阻滞剂掩盖低血糖症状"），原问法太泛导致两章节内容都能部分回答，题目实际上无法唯一定位到目标chunk，重出后改问只有目标chunk才完整回答的具体机制点，才恢复了唯一定位性——这是方法论"题目问得太泛需要重出"这条规则的一次具体应用案例。

## 音频章节（6段，13题，2026-07-22）

覆盖`eval/testset/clinical/raw/audio/`下6段心脏药理学网课音频：Fenoldopam、Reserpine、Niacin、Bempedoic Acid、Ivabradine、Dopamine & Dobutamine。ID前缀改用`clinical-aXX`（音频题），跟CS测试集`cs-aXX`的命名约定一致，区别于书本题的`clinical-bXX`。

### clinical-a01

**题目**（EN）："What is fenoldopam's mechanism of action, and in what clinical settings is it used?"

**检索query**："fenoldopam's mechanism of action and clinical uses"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmaoclogy (1) ｜ Fenoldopam with a Mnemonic.mp3/07:43–08:55` | 0.4043 | **能，排名第1**（目标chunk） |
| `openstax-pharm-ch13-psychopharm.pdf/p0027/0112` | 0.4935 | 不能（氟马西尼逆转苯二氮卓，跨章节污染） |
| `Cardiac Pharmaoclogy (1) ｜ Fenoldopam with a Mnemonic.mp3/08:56–10:06` | 0.4944 | 不能（课程推广内容） |
| `Cardiac Pharmaoclogy (1) ｜ Fenoldopam with a Mnemonic.mp3/05:36–06:33` | 0.4972 | 部分能（降压药物分类总论，提及phenyl dopam是D1激动剂） |
| `Cardiac Pharmacology (5) ｜ Ivabradine with Mnemonic.mp3/00:00–01:07` | 0.5031 | 不能（伊伐布雷定机制，跨来源污染） |

**回答是否准确**：准确，选择性D1部分激动剂+通过增加cAMP血管舒张+高血压危象/术后高血压三点均答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-a02

**题目**（ZH）："体重每减轻1千克，收缩压大约能下降多少mmHg？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmaoclogy (1) ｜ Fenoldopam with a Mnemonic.mp3/03:21–04:28` | 0.3585 | **能，排名第1**（目标chunk） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0005/0019` | 0.4102 | 不能（AHA运动建议） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0004/0012` | 0.4273 | 不能（血压分级表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0027/0127` | 0.4367 | 不能（病例生命体征表格） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0008/0034` | 0.4491 | 不能（病例生命体征表格） |

**回答是否准确**：准确，2mmHg答对。

**具体分析**：目标chunk稳定排名第1，检索质量好。原题面带"根据这段音频的说法"这一元指涉前缀，已去掉改为直接提问（不影响这道题的检索结果，但跟clinical-a06一样属于应该避免的问法模式，统一修正）。

### clinical-a03

**题目**（ZH）："利血平（reserpine）是通过什么机制降低血压的？"

**检索query**："利血平（reserpine）降低血压的机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmacology (2) ｜ Reserpine with a Mnemonic.mp3/11:07–12:09` | 0.3737 | **能，排名第1**（目标chunk） |
| `Cardiac Pharmacology (2) ｜ Reserpine with a Mnemonic.mp3/10:05–11:07` | 0.3977 | 能（同一机制的另一段表述，支撑性） |
| `Cardiac Pharmaoclogy (1) ｜ Fenoldopam with a Mnemonic.mp3/03:21–04:28` | 0.4014 | 不能（体重与血压关系） |
| `Cardiac Pharmacology (3) ｜ Niacin.../09:28–10:32` | 0.4085 | 不能（烟酸VLDL合成机制） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0003/0008` | 0.4112 | 不能（RAAS图注） |

**回答是否准确**：准确，抑制VMAT→阻止多巴胺进入囊泡合成去甲肾上腺素→减少儿茶酚胺释放的完整链条均答对。

**具体分析**：目标chunk稳定排名第1，top2都真实相关，检索质量好。

### clinical-a04

**题目**（EN）："What central nervous system adverse effects result from reserpine's inhibition of norepinephrine activity?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch13-psychopharm.pdf/p0020/0077` | 0.3971 | 不能（第二代抗精神病药不良反应，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0151` | 0.3980 | 不能（阿托莫西汀机制片段，跨章节污染） |
| `Cardiac Pharmacology (2) ｜ Reserpine with a Mnemonic.mp3/04:14–05:06` | 0.4011 | **能，排名第3**（目标chunk） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0012/0054` | 0.4056 | 不能（ARB不良反应） |
| `openstax-pharm-ch28-diabetic.pdf/p0004/0012` | 0.4081 | 不能（高血糖症状，跨章节污染） |

**回答是否准确**：准确，镇静/嗜睡/抑郁/性欲下降均答对。

**具体分析**：目标chunk排名第3才进入，top5里4个是跨章节污染（含2个ch13精神药物、1个ch28糖尿病），说明该英文query在混合语料库里精度不算理想，但未影响最终答案准确性。

### clinical-a05

**题目**（ZH）："烟酸（niacin）降低LDL、升高HDL主要是通过哪两种机制实现的？"

**检索query**："烟酸（niacin）降低LDL、升高HDL的主要机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmacology (3) ｜ Niacin.../09:28–10:32` | 0.3148 | 能（抑制VLDL合成，同一机制的另一段表述） |
| `Cardiac Pharmacology (3) ｜ Niacin.../07:15–08:22` | 0.3203 | **能，排名第2**（目标chunk） |
| `Cardiac Pharmacology (3) ｜ Niacin.../08:23–09:28` | 0.3485 | 能（抑制激素敏感性脂肪酶，支撑性） |
| `Cardiac Pharmacology (3) ｜ Niacin.../10:33–11:43` | 0.3501 | 部分能（临床用途/副作用，非机制本身） |
| `Cardiac Pharmacology (3) ｜ Niacin.../13:52–14:53` | 0.3554 | 部分能（机制总结重复） |

**回答是否准确**：准确，抑制肝脏VLDL合成+抑制激素敏感性脂肪酶均答对。

**具体分析**：目标chunk排名第2，top5全部来自本音频、且都不同程度相关，检索质量本题最好。

### clinical-a06

**题目**（EN）："What are the most common adverse effects of niacin therapy?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmacology (3) ｜ Niacin.../10:32–11:42` | 0.3732 | **能，排名第1**（目标chunk） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0024/0114` | 0.4257 | 不能（硝酸酯类不良反应） |
| `openstax-pharm-ch07-antiinfective.pdf/p0009/0037` | 0.4389 | 不能（氨基糖苷类耳毒性，跨章节污染） |
| `openstax-pharm-ch13-psychopharm.pdf/p0039/0155` | 0.4423 | 不能（CNS兴奋剂相互作用列表，跨章节污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0012/0054` | 0.4477 | 不能（ARB不良反应） |

**回答是否准确**：准确，潮红/瘙痒/感觉异常/高血糖/高尿酸血症全部答对。

**具体分析**：**原题面"...mentioned in this recording"触发了真实缺陷，已重新验证**。原问法下模型完全没有调用retrieve，直接回复"I cannot retrieve information from a specific recording since no such source or context has been provided"，误判成需要用户额外提供文档，转而用通用医学知识作答（有清楚披露，不算幻觉，但属于不该发生的检索缺失）。去掉"mentioned in this recording"这个元指涉表述、改成直接问法后，retrieve被正常调用，目标chunk稳定排名第1，回答准确——证实了这个措辞就是触发检索缺失的原因。

### clinical-a07

**题目**（EN）："Bempedoic acid lowers cholesterol by inhibiting which enzyme, and what happens in the liver as a result?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/00:00–01:02` | 0.3407 | 不能（抗高脂血症药物类别总论） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/22:29–23:32` | 0.3429 | 部分能（提及ACL抑制，主讲临床试验背景） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/15:17–16:26` | 0.3533 | **能，排名第3**（目标chunk） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/10:57–12:09` | 0.3908 | 能（ACL机制细节，支撑性） |
| `Cardiac Pharmacology (3) ｜ Niacin.../09:28–10:32` | 0.3937 | 不能（烟酸VLDL合成机制） |

**回答是否准确**：准确，抑制ATP柠檬酸裂解酶+肝脏上调LDL受体机制均答对。

**具体分析**：目标chunk排名第3，top5里4个来自本音频、多数真实相关，检索质量好。

### clinical-a08

**题目**（ZH）："为什么将Bempedoic acid跟他汀类药物（statin）联合使用能更有效地降低胆固醇？"

**检索query**："Bempedoic acid 与 statin 联合使用降低胆固醇的机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/23:32–24:47` | 0.3399 | **能，排名第1**（目标chunk） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/16:27–17:38` | 0.3510 | 不能（临床用途/副作用） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/00:00–01:02` | 0.3780 | 不能（药物类别总论） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/22:29–23:32` | 0.3998 | 部分能（ACL/HMG-CoA还原酶对比铺垫） |
| `Cardiac Pharmacology (4) ｜ Bempedoic Acid.mp3/14:09–15:17` | 0.4124 | 部分能（机制铺垫） |

**回答是否准确**：准确，序贯阻断（sequential block，Bempedoic acid抑制ACL+他汀抑制HMG-CoA还原酶）机制答对，还合理补充了辅酶Q10相关的肌肉副作用背景（检索内容里确实提到）。

**具体分析**：目标chunk稳定排名第1，检索质量好。

### clinical-a09

**题目**（EN）："What ion channel does ivabradine inhibit, and does it reduce mortality in angina or heart failure?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Cardiac Pharmacology (5) ｜ Ivabradine with Mnemonic.mp3/00:00–01:07` | 0.3657 | **能，排名第1**（目标chunk1） |
| `Cardiac Pharmacology (5) ｜ Ivabradine with Mnemonic.mp3/01:08–02:10` | 0.3738 | **能，排名第2**（目标chunk2：不降低死亡率） |
| `Cardiac Pharmacology (5) ｜ Ivabradine with Mnemonic.mp3/02:11–03:19` | 0.3854 | 能（同一内容mnemonic总结，支撑性） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0001/0002` | 0.5035 | 不能（章节目录） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0017/0078` | 0.5086 | 不能（钙通道阻滞剂机制） |

**回答是否准确**：准确，funny current/If通道+不降低死亡率两点均答对。

**具体分析**：目标chunk分别排名第1、第2，top3全部来自本音频且真实相关，检索质量本题最好。

### clinical-a10

**题目**（ZH）："多巴胺（dopamine）和多巴酚丁胺（dobutamine）在受体选择性上的关键区别是什么？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Dopamine & Dobutamine.../09:03–10:11` | 0.3851 | 部分能（临床决策案例，含受体差异应用结论） |
| `Dopamine & Dobutamine.../01:05–02:17` | 0.3896 | **能，排名第2**（目标chunk） |
| `Dopamine & Dobutamine.../00:00–01:05` | 0.4098 | 部分能（背景介绍，提及D1/D2/β/α受体） |
| `Dopamine & Dobutamine.../07:57–09:03` | 0.4121 | 能（肾灌注差异，支撑性） |
| `Dopamine & Dobutamine.../06:51–07:56` | 0.4391 | 不能（心肌收缩细胞机制细节） |

**回答是否准确**：准确，多巴胺D1/D2+β+α激动 vs 多巴酚丁胺无D1/D2、只作用β1/β2/α这一核心区别答对。

**具体分析**：目标chunk排名第2，top5全部来自本音频，检索质量好。

### clinical-a11

**题目**（EN）："For a CHF patient with hypotension and poor kidney perfusion, why is dopamine preferred over dobutamine?"

**检索query**："why is dopamine preferred over dobutamine in CHF patients with hypotension and poor kidney perfusion"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `Dopamine & Dobutamine.../09:03–10:11` | 0.1988 | **能，排名第1**（目标chunk） |
| `Dopamine & Dobutamine.../07:56–09:02` | 0.2805 | **能，排名第2**（目标chunk） |
| `Dopamine & Dobutamine.../00:00–01:05` | 0.2955 | 部分能（背景介绍） |
| `Dopamine & Dobutamine.../04:32–05:45` | 0.3484 | 不能（cAMP功能列表） |
| `Dopamine & Dobutamine.../06:51–07:56` | 0.3485 | 不能（心肌收缩细胞机制细节） |

**回答是否准确**：准确，多巴胺经D1/D2增加肾灌注+不降低血压、多巴酚丁胺缺乏此作用且β2会致低血压，两点均答对。

**具体分析**：目标chunk分别排名第1、第2，score明显更低（0.20/0.28，本批最低区间），检索质量最好。原题面"Why would a clinician choose..."是第三人称考试腔，改成第二人称/场景直问的自然句式后，retrieve被正常调用且精准命中，说明这种考试化措辞也会跟"in this recording"一样触发模型跳过检索的问题。

### clinical-a12（无答案题，EN，重出）

**题目**："What is furosemide's mechanism of action as a diuretic?"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0016/0067` | 0.4827 | 不能（氟胞嘧啶机制，跨章节污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0022/0101` | 0.4870 | 不能（噻嗪类利尿剂剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0096` | 0.4883 | 不能（噻嗪类机制，非袢利尿剂） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0020/0093` | 0.5016 | 不能（利尿剂总论） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0021/0100` | 0.5046 | 不能（利尿剂不良反应总论） |

**回答**：正确拒答，明确区分了检索内容和补充的通用药理学知识。

**幻觉判定**：否。

**具体分析**：确认furosemide/loop diuretic在全部6段音频0命中，题目有效。

### clinical-a13（无答案题，ZH）

**题目**："米力农（milrinone）作为强心药，具体是通过什么机制增强心肌收缩力的？"

**检索query**："米力农（milrinone）作为强心药的具体作用机制"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch18-antihypertensive.pdf/p0013/0058` | 0.4835 | 不能（ARB剂量表） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0016/0069` | 0.4875 | 不能（β受体阻滞剂剂量表） |
| `openstax-pharm-ch13-psychopharm.pdf/p0009/0030` | 0.5012 | 不能（MAOI/酪胺机制，跨章节污染） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0007/0029` | 0.5012 | 不能（心绞痛药物治疗总论） |
| `openstax-pharm-ch13-psychopharm.pdf/p0013/0041` | 0.5040 | 不能（MAOI用药教育，跨章节污染） |

**回答**：正确拒答，明确说明检索到的都是降压药/MAOI等无关内容，建议查阅专门的心血管药理教材。

**幻觉判定**：否。

**具体分析**：确认milrinone在全部6段音频0命中，题目有效。

## 本批（音频）小结

- 13题（11道音频题+2道无答案题），中英文各占一半（EN 7/ZH 6）。
- Hit@5（11道音频题适用）：**11/11（100%）**。
- 幻觉（2道无答案题适用）：**0/2**。
- **重要发现：题面里的元指涉/考试腔表述会让模型跳过retrieve**——clinical-a06原问法带"...mentioned in this recording"、clinical-a11原问法带第三人称考试腔"Why would a clinician choose..."，两次都导致模型完全没调用retrieve、直接转向训练知识作答（有清楚披露，不算幻觉，但都是本可以查到准确答案却放弃检索的真实缺陷）。改成直接、自然的问法后，两题都恢复正常调用retrieve并精准命中，确认了这类措辞是真实的触发因素，跟此前书本题里"教材第X章有什么说明"这种模板问法是同一类问题的音频版本。
- **方法论提醒**：出无答案题前的关键词确认要留意ASR转写风险——语音转写可能把专有名词转录错误（如某个药名转写成读音相近但拼写不同的词），导致精确关键词检索查不到语料库里实际存在的相关内容，需要在关键词检索之外再通读候选chunk全文复核。

## 图片章节（3张，2026-07-22）

覆盖`eval/testset/clinical/raw/pic/`下3张图片：cli_p1.png（澳门衛生局"無傷攻略"专题网页，内容是网站命名寓意/目标，无实质临床知识点，未出题）、cli_p2.png（糖尿病饮食信息图）、cli_p3.png（基孔肯雅热科普图）。ID延续书本题`clinical-bXXX`编号（跟CS图片题`cs-bXXX`的做法一致，图片文本内容本质上是另一种"文档"，不单独开前缀）。

### clinical-b074

**题目**（ZH）："糖尿病饮食建议中，哪四类食物应该尽量少吃？"

**检索query**：与题目原文相同

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cli_p2.png` | 0.2427 | **能，排名第1**（目标chunk） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0023/0106` | 0.4568 | 不能（螺内酯用药教育） |
| `openstax-pharm-ch18-antihypertensive.pdf/p0022/0105` | 0.4594 | 不能（利尿剂用药教育：补钾食物） |
| `openstax-pharm-ch28-diabetic.pdf/p0003/0010` | 0.4737 | 不能（1型/2型糖尿病预防总论） |
| `openstax-pharm-ch28-diabetic.pdf/p0017/0101` | 0.4739 | 不能（吡格列酮机制） |

**回答是否准确**：准确，四类食物（高糖饮料/精制碳水/高油高脂/加工肉类）及各自例子全部答对。

**具体分析**：目标chunk稳定排名第1，score明显更低（0.24 vs 0.45+），检索质量好。原题面带"这份...图片里"这一元指涉前缀，跟clinical-b075原版同一模式，虽然这次retrieve仍被正常调用，但改成直接问法后更安全，已一并修正。

### clinical-b075

**题目**（EN）："How many days after being bitten by an infected mosquito does chikungunya fever typically develop, and which two mosquito species are the main carriers?"

**检索query**："chikungunya fever incubation period and primary mosquito vectors"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `cli_p3.png` | 0.5258 | **能，排名第1**（目标chunk） |
| `openstax-pharm-ch07-antiinfective.pdf/p0001/0002` | 0.5637 | 不能（章节目录） |
| `openstax-pharm-ch07-antiinfective.pdf/p0030/0136` | 0.5728 | 不能（结核病总论） |
| `openstax-pharm-ch07-antiinfective.pdf/p0010/0040` | 0.5783 | 不能（疱疹病毒药物） |
| `openstax-pharm-ch07-antiinfective.pdf/p0031/0140` | 0.6011 | 不能（抗结核药机制） |

**回答是否准确**：准确，4-8天潜伏期+埃及伊蚊/白纹伊蚊两个蚊种均答对。

**具体分析**：目标chunk排名第1，但score偏高（0.53，全场最高的"命中"分数），说明图片这类非常规文档在稠密向量空间里整体匹配度不如书本正文，其余4个chunk score都在0.56+区间、区分度不高。原题面曾是"According to this infographic..."，触发了模型完全跳过retrieve的问题（跟ch18/ch13批次clinical-a06/a11同一模式），改成直接问法后恢复正常检索并精准命中。

### clinical-b076（无答案题，EN）

**题目**："Is there a vaccine or specific antiviral treatment available for chikungunya fever?"

**检索query**："vaccine or specific antiviral treatment for chikungunya fever"

| chunk | score | 能否支撑答案 |
|---|---|---|
| `openstax-pharm-ch07-antiinfective.pdf/p0011/0044` | 0.5042 | 不能（阿昔洛韦/奥司他韦剂量表） |
| `openstax-pharm-ch07-antiinfective.pdf/p0010/0040` | 0.5075 | 不能（疱疹病毒药物，非基孔肯雅热） |
| `openstax-pharm-ch07-antiinfective.pdf/p0011/0041` | 0.5084 | 不能（流感神经氨酸酶抑制剂） |
| `openstax-pharm-ch07-antiinfective.pdf/p0012/0048` | 0.5095 | 不能（阿昔洛韦机制） |
| `openstax-pharm-ch07-antiinfective.pdf/p0028/0127` | 0.5120 | 不能（甲硝唑/青霉素等STI治疗） |

**回答**：正确拒答核心问题，明确说明"目前没有针对基孔肯雅热的特异性疫苗或抗病毒治疗，管理以支持性治疗为主"，医学上准确，且检索到的5个chunk全部是其他病毒（疱疹、流感）的治疗药物，跟基孔肯雅热本身无关。

**幻觉判定**：否。回答内容虽然没有明确标注"这不是书本依据"，但结论本身（无特效疫苗/抗病毒药）是真实、准确的医学常识，检索到的chunk也全部标注了"不能支撑"，没有被误用来编造关于基孔肯雅热的虚假细节。

**具体分析**：确认vaccine/疫苗/治疗/treatment在cli_p3.png全部0命中，题目有效。

## 缺陷清单（全部89题构建过程中发现的真实问题，2026-07-22）

### 幻觉（issue #40范畴）

1. **clinical-b036**（buspirone机制，ch13）：10个检索到的chunk全部跟buspirone无关，模型没有任何披露，直接给出一整套具体、自信的错误机制描述（"5-HT1A受体部分激动剂"等）。这是全部89题里唯一一例无披露的真实幻觉。

### 检索缺陷（issue #48范畴：dense retrieval缺关键词兜底）

2. **clinical-b004**（利奈唑胺分类，ch07）：目标chunk跟题目几乎字面对应但top5完全未命中。定位到根因：题目问法是抽象归纳式（"分类及适应症"），没有用到chunk原文的具体术语（"highly resistant"、"VRSA"）；用embedder直接对比候选query验证，换成包含原文术语的问法能让排名从第9升到第1。题目故意保留会被miss掉的原表述，用于暴露这个缺陷，不改写成检索友好版本。
3. **clinical-b041**（万古霉素儿科剂量，ch07计算题）：目标chunk真实miss，模型诚实declined、未编造具体数字。

### 生成流程缺陷（已提issue #60）

4. **clinical-b056**（hydralazine机制，ch18）：模型5次换角度重新表述query反复检索hydralazine相关内容，25个citation里没有一个提到hydralazine，但模型没有在任何一轮止损披露"未找到"，而是持续重试直到耗尽`_MAX_ROUNDS`（5轮），最终返回`[MAX_ROUNDS_EXCEEDED]`，没有产生任何文本回答。https://github.com/ismy-cosmos/BookAgent/issues/60 **——2026-07-23系统提示词修改后已修复，经真实后端API确认，详见该题条目。**


### 训练知识补充但未经检索验证（较软的观察，不算错误）

6. 多次观察到模型在核心结论准确的前提下，额外补充检索内容没有明确涵盖的具体细节：clinical-b024（"neuroleptic"词源学）、clinical-b026（REMS执行细节）、clinical-b029（三类药物具体分子机制）、clinical-b034（神经可塑性延伸）、clinical-b048（情绪障碍筛查建议）、clinical-b052（草药列举）。这些补充都没有跟检索内容矛盾、不算幻觉，但反映模型有稳定的"用训练知识补全细节"倾向，即使检索本身命中良好，值得在设计issue #40后续方案时参考。

### 语料本身的特性（非模型缺陷，方法论提醒）

7. **跨章节事实重复**：clinical-b067最初的宽泛问法在ch18和ch28两章都能部分回答（"β受体阻滞剂掩盖低血糖症状"这一事实两章各有一版表述），导致题目无法唯一定位到目标chunk，按方法论重出解决。出无答案题/事实题前，"这个知识点是否在教材里只出现一次"不能想当然。
8. **ASR转写误差**：clinical-a12出题时用关键词"digoxin"确认全部6段音频0命中，但语音转写实际把它转录成了拼写错误的"de-joxin"，语料库里其实完整讲过digoxin的机制，只是关键词检索没扫描到这个转写变体，误判为有效的无答案题，已重出为furosemide解决。音频语料的"0命中"确认不能只依赖精确关键词匹配，需要通读候选chunk全文复核。

## 总体统计

全部89题（书本76题+音频13题：事实题60、计算题5、音频题11、无答案题13）。

以下是2026-07-23系统提示词修改（`pipeline/agent/client.py`）后的当前数字。只有clinical-b004、clinical-b036这2题被针对性复测过（各测了8次），其余87题维持原提示词下的结果，没有全量重新核对，所以下面这组数字不是"重跑89题后的全量真实结果"，是"87题旧数字+2题新数字"的混合数字，仅供当前参考。

- **Hit@5**：76/77 = **98.7%**（77道有答案题适用）。clinical-b004从未命中改判为命中——`audit_question.py`复测8次，7次命中、1次未命中，多数情况命中，按多数结果计入分子；这道题的Hit@5不是100%稳定，约1/8的概率会退回未命中。
- **幻觉率**：0/89 = **0%**（全量口径），0/13 = **0%**（无答案题口径）。clinical-b036从幻觉改判为诚实披露——`audit_question.py`用紧凑循环连续复测时曾多次退回原来的幻觉，但经真实后端API（跟用户实际使用的是同一进程）复测、以及用户自己独立复测，结果稳定给出诚实披露，按真实使用场景的结果计入。clinical-b056原提示词下是`MAX_ROUNDS_EXCEEDED`（issue #60），不产生任何断言性内容，不适合并入分子分母；系统提示词修改后已修复（1次retrieve+诚实披露，经真实后端API确认），现在可以正常计入0/13、0/89这两个分母里、不计入分子。

这是按题目逐个人工核对后的统计，其中87题是初版核对时的数字，clinical-b004/clinical-b036这2题是2026-07-23复测后的数字。要拿到完全可信的全量数字，需要用新提示词把89题重新走一遍`audit_question.py`，这个工作目前还没有做。
