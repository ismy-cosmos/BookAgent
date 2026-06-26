# 解析器选型测试语料候选记录

记录日期：2026-06-26  
分支：feat/w2-parser-selection  
用途：追踪三学科测试语料的搜寻进度，供后续筛选与补充

---

## 当前选定（第一轮）

| 学科 | 书目 | 状态 |
|---|---|---|
| CS | OSTEP — Operating Systems: Three Easy Pieces | ✅ 选定 |
| 临床医学 | Nursing Pharmacology（NCBI Bookshelf） | ✅ 选定（药理学代表学科） |
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

### ✅ Nursing Pharmacology（NCBI Bookshelf）
- **来源**：[ncbi.nlm.nih.gov/books/NBK595000/](https://www.ncbi.nlm.nih.gov/books/NBK595000/)
- **许可**：CC-BY 4.0
- **内容**：药代动力学公式（Vd、CL、t½）、给药方案表、剂量计算、药物分类、副作用
- **解析挑战覆盖**：药代动力学公式（含分数/指数）、多列剂量表、概念图
- **限制**：护理层级，非内科/诊断级别；无原生音频
- **音频**：需配开放课程讲座（如 Yale 医学/药理相关录音）
- **备注**：用户确认接受药理学作为临床医学代表学科

### 🔍 Fundamentals of Nursing Pharmacology（BC Open）
- **来源**：[opentextbc.ca/nursingpharmacology/](https://opentextbc.ca/nursingpharmacology/)
- **许可**：CC-BY 4.0
- **内容**：与 NCBI 版本类似，含药物分类表、副作用矩阵、测验和概念图
- **状态**：备选，NCBI 版本优先

### 🔍 Clinical Pharmacology（archive.org 旧版教材）
- **来源**：[archive.org/details/ClinicalPharmacology](https://archive.org/details/ClinicalPharmacology)
- **许可**：archive.org 托管，版权状态需确认
- **内容**：传统临床药理学教材，更接近"临床"层级
- **状态**：备用（若 Nursing Pharmacology 解析难度不足）

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
| 临床医学 | Yale Open Courses 药理学相关；Khan Academy | 待搜寻 |
| 法学 | 法学院公开课 podcast；Yale Law 讲座 | 待搜寻 |

---

## 搜寻历史

| 日期 | 搜寻内容 | 结论 |
|---|---|---|
| 2026-06-26 | OSTEP 内容核实 | ✅ 通过全部 CS 材料要求 |
| 2026-06-26 | 临床医学开放教材（含公式+表格+许可） | 找到 Nursing Pharmacology × 2；archive.org 旧版备用 |
| 2026-06-26 | 法学开放案例教材（CALI eLangdell） | 找到 Criminal Procedure + Torts 7th Ed |
