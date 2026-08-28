# 解析器选型测试语料候选记录

记录日期：2026-06-26  
分支：feat/w2-parser-selection  
用途：追踪三学科测试语料的搜寻进度，供后续筛选与补充

---

## 当前选定（第一轮）

| 学科 | 书目 | 状态 |
|---|---|---|
| CS | OSTEP — Operating Systems: Three Easy Pieces | ✅ 选定 |
| 临床医学 | ~~Nursing Pharmacology（NCBI Bookshelf）~~ → OpenStax《Pharmacology for Nurses》选4章 | ✅ 2026-07-21 重新选定，原因见下 |
| 法学 | Criminal Procedure（CALI eLangdell） | ✅ 选定（刑事诉讼） |

---

## CS 候选

### ✅ OSTEP — Operating Systems: Three Easy Pieces
- **来源**：[pages.cs.wisc.edu/~remzi/OSTEP/](https://pages.cs.wisc.edu/~remzi/OSTEP/)
- **许可**：CC-BY-NC-ND 3.0，按章节 PDF 分发，免费
- **作者**：Remzi H. Arpaci-Dusseau & Andrea C. Arpaci-Dusseau（UW-Madison）
- **内容**：虚拟化（进程/内存）、并发、持久化，C 代码贯穿全书，xv6 内核实例
- **解析挑战覆盖**：
  - 代码块（C 语言，含内核态片段）
  - 图表（进程状态机、内存布局、磁盘结构）
  - 计算题（调度周转时间/响应时间、虚拟地址翻译、磁盘寻道时间、RAID 容量）
  - LLM 难以凭记忆回答（worked example 精确数值、特定 page table entry 格式）
- **音频**：无原生音频；配套使用 MIT OCW 6.S081 YouTube 讲座录音（公开）
- **核实状态**：✅ 通过全部 CS 材料要求

---

## 临床医学候选

### ❌ Nursing Pharmacology（NCBI Bookshelf）——已放弃（2026-07-21）
- **来源**：[ncbi.nlm.nih.gov/books/NBK595000/](https://www.ncbi.nlm.nih.gov/books/NBK595000/)
- **许可**：CC-BY 4.0
- **放弃原因**：965页真实 ingest 测试中，issue #24（大PDF分批解析）反复 OOM，排查发现是该书本身 PDF 质量问题——多处药物分类表格（Penicillin、Sulfonamides 等章节）被 marker 解析成散乱文本而非表格结构，确认至少2个独立实例（原书第198、208页），非孤立个案。该书源自 `wtcs.pressbooks.pub/pharmacology2e`（Pressbooks 平台导出），怀疑是这类 OER 导出平台的通病。批大小从100调到25页仍无法稳定绕开，判定不可靠，改换材料

### ✅ OpenStax《Pharmacology for Nurses》——选4章，2026-07-21 选定
- **来源**：[openstax.org/details/books/pharmacology](https://openstax.org/details/books/pharmacology)，直接PDF：[assets.openstax.org/.../Pharmacology-WEB.pdf](https://assets.openstax.org/oscms-prodcms/media/documents/Pharmacology-WEB.pdf)
- **许可**：CC BY-NC-SA 4.0
- **整书**：1229页，Prince XML 排版（非 Pressbooks 家族，排版质量与 Nursing Pharmacology 不同源）
- **选定4章**（不用整本，实测每章表格解析质量后选定，覆盖4个不同身体系统；已裁掉每章末尾 Chapter Summary/Key Terms/Review Questions 这类无答案的冗余材料，合计130页）：

| 文件（`eval/testset/clinical/raw/book/`） | 章节 | 原始PDF页码 | 裁剪后页数 | 含表格页数(裁剪前统计) |
|---|---|---|---|---|
| openstax-pharm-ch07-antiinfective.pdf | Ch.7 抗感染药物 | 207-244(原207-248,删去239-248) | 38 | 18/42 |
| openstax-pharm-ch13-psychopharm.pdf | Ch.13 精神药物 | 407-448(原407-452,删去449-452) | 42 | 25/46 |
| openstax-pharm-ch18-antihypertensive.pdf | Ch.18 抗高血压/抗心绞痛药物 | 537-563(原537-566,删去564-566) | 27 | 16/30 |
| openstax-pharm-ch28-diabetic.pdf | Ch.28 糖尿病药物 | 783-805(原783-808,删去806-808) | 23 | 8/26 |

- **实测验证**：4章均用真实 marker 全量跑过 layout+OCR+table，无崩溃；抽查多页表格（Table 7.1 抗生素分类表、Table 13.9 抗抑郁药分类表等）均正确识别为 Table block，肉眼核对内容清晰，未复现 Nursing Pharmacology 的表格误判问题
- **解析挑战覆盖**：同款"Drug Class/Mechanism/Dosage/Nursing Considerations/Adverse Effects"多列药物分类表、剂量计算、跨身体系统覆盖（感染/精神/心血管/内分泌）
- **音频**：见下方"音频资源待定"

### 🔍 Fundamentals of Nursing Pharmacology（BC Open）——不再考虑
- **来源**：[opentextbc.ca/nursingpharmacology/](https://opentextbc.ca/nursingpharmacology/)
- **许可**：CC-BY 4.0
- **状态**：2026-07-21 真实调研确认属于 Pressbooks/BC Open 生态（跟 Nursing Pharmacology 同源风险），未做提取验证即排除，不再作为备选

### 🔍 Clinical Pharmacology（archive.org 旧版教材）——不再考虑
- **来源**：[archive.org/details/ClinicalPharmacology](https://archive.org/details/ClinicalPharmacology)
- **许可**：archive.org 托管，版权状态需确认
- **状态**：OpenStax 方案已验证可用，不再需要此备选

---

## 法学候选

### ✅ Criminal Procedure（CALI eLangdell）
- **来源**：[cali.org/books/criminal-procedure-trachtenberg-alexander](https://www.cali.org/books/criminal-procedure-trachtenberg-alexander)
- **许可**：CC-BY-NC-SA（CALI eLangdell）
- **作者**：Ben Trachtenberg & Anne Alexander（University of Missouri）
- **内容**：第四/五/六修正案条文、案件引用（案名+法院+年份）、判决要旨
- **解析挑战覆盖**：
  - 法条原文（密集文本 + 编号结构）
  - 案件引用表格（案名、法院、年份、判决要点）
  - 判决逻辑段落（嵌套引用）
  - LLM 难以凭记忆回答（具体案件编号和判决细节）
- **音频**：无原生音频；需配法学院公开课录音
- **状态**：✅ 选定

### 🔍 Torts: Cases, Principles, and Institutions（7th Ed）
- **来源**：[cali.org/sites/default/files/FINAL-Witt_Tani-TCPI-7thEd-July2025.pdf](https://www.cali.org/sites/default/files/FINAL-Witt_Tani-TCPI-7thEd-July2025.pdf)
- **许可**：CC
- **内容**：侵权案例、赔偿计算、判决逻辑表格
- **状态**：备选（用户选择刑事诉讼优先）

---

## 音频资源待定

三学科均需 2–3 段讲座录音（每段 ≤5 min），来源与主教材可不同，主题对齐即可。

| 学科 | 音频候选方向 | 状态 |
|---|---|---|
| CS | MIT OCW 6.S081（YouTube，公开讲座） | 待确认可下载 MP3 |
| 临床医学 | ✅ 已下载：Medicosis Perfectionalis《Cardiac Pharmacology》系列6集（心血管药物：Fenoldopam/Reserpine/Niacin/Bempedoic Acid/Ivabradine/多巴胺-多巴酚丁胺），来自[频道](https://www.youtube.com/@MedicosisPerfectionalis)播放列表，总时长80.6分钟(约1.34小时)，已存`eval/testset/clinical/raw/audio/` | 2026-07-21 确定。主题跟已选定的 Ch.18 抗高血压/抗心绞痛章节直接对应，比通用《General Pharmacology》系列更贴题 |
| 法学 | 法学院公开课 podcast；Yale Law 讲座 | 待搜寻 |

---

## 搜寻历史

| 日期 | 搜寻内容 | 结论 |
|---|---|---|
| 2026-06-26 | OSTEP 内容核实 | ✅ 通过全部 CS 材料要求 |
| 2026-06-26 | 临床医学开放教材（含公式+表格+许可） | 找到 Nursing Pharmacology × 2；archive.org 旧版备用 |
| 2026-06-26 | 法学开放案例教材（CALI eLangdell） | 找到 Criminal Procedure + Torts 7th Ed |
| 2026-07-21 | Nursing Pharmacology 965页真实ingest测试 | 发现表格解析系统性质量问题（Pressbooks导出通病），放弃该书 |
| 2026-07-21 | 页数更少+质量可靠的替代临床教材 | 调研多个候选均无法同时满足全部要求（页数/许可/表格复杂度/非Pressbooks/配套音频）；改路线：从确认无风险的 OpenStax 整书（1229页）里选取4个高质量章节（144页），实测验证通过 |
