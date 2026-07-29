# 离线中英检索翻译服务选型（范围重置）

**状态**：已纠正选型对象；尚未安装、调用外部服务或改生产代码。  
**边界**：本文件只讨论 `q_raw` 的 EN↔ZH 翻译服务。它不属于 BGE-M3 sparse 实验，也不涉及 LLM 改写、翻译模型训练、微调、术语扩展或 reranker。

## 1. 正确的决策对象：翻译服务，不是翻译模型/引擎

要复现的是 CLIR 中常见的 query-translation 结构：

```text
q_raw（源语言原题）
  -> 现成翻译服务
  -> q_trans（目标语言）
  -> 目标语言 BM25
```

NeuCLIR 的官方概览明确写明：赛道提供的 query machine translation 由 **online Google Translate service** 产生；其 BM25 `QGT` run 用这些 machine-translated queries 检索原生语言文档。换言之，研究系统把 Google Translate 当成一个现成黑盒服务，并不选择、更不训练其内部翻译模型。

因此，本项目也应在同一层选型：找一个能本地运行、可程序调用的 EN↔ZH **翻译服务/API**。服务内部使用何种翻译引擎只是实现依赖，不能和 Google/Azure 作为并列方案比较。

## 2. 本项目的硬边界

- 输入只允许 `q_raw`；不复用 LLM、不生成扩展 query、不添加解释或同义词。
- 翻译后直接进入目标语言 lexical/BM25 索引。
- 服务须能离线/本地部署，且由程序以 HTTP API 或等价非交互接口调用。
- 必须免费，且服务代码和实际 EN↔ZH 语言包都要有明确可商用许可。
- 首要质量指标是词义和术语保真；句子是否自然不是目标。
- 不要求、也不计划训练或微调任何翻译模型。

“不得造词/错译”是对翻译服务质量的验收要求，不应被偷换成 query expansion 或另建检索架构。

## 3. 候选应如何归类

| 项目 | 与 Google/Azure 是否同一决策层 | 是否符合本地免费方向 | 结论 |
| --- | --- | --- | --- |
| **Google Translate API / Azure Translator API** | 是：现成翻译服务/API | 否：在线且付费 | 是 NeuCLIR 式正确参照物，但不满足本项目部署约束。 |
| **LibreTranslate** | **是：可自托管 REST 翻译 API** | **是，待逐项核验 EN↔ZH 包许可** | 当前唯一应当作为首要离线候选审视的服务级产品。调用方只需 `POST /translate`，不涉及训练。 |
| Argos Translate | 否：LibreTranslate 的底层翻译库 | 不单独作为系统方案 | 它不是和 Google/Azure 并列的选型项；仅是 LibreTranslate 的实现依赖。 |
| Marian、Moses、OpenNMT 等 | 否：推理/训练工具包 | 不符合“现成翻译服务” | 不进入本轮候选。让项目自己选权重、搭服务或训练，已超出任务。 |
| OmegaT / CAT / TM 工具 | 否：人工翻译辅助工具 | 不符合自动 query 翻译接口 | 可做人工翻译工作流，不能代替本链路中的基础翻译服务。 |

## 4. LibreTranslate 的准确定位

LibreTranslate 官方将自己定义为可完全 self-host 的开源 machine-translation API，并明确将 Google/Azure 作为它所替代的专有 API；官方 quickstart 直接提供本地启动和 `POST /translate` 调用。这正是本项目所需的部署/调用层级。

它的局限也应如实记录：

- 服务代码是 AGPL-3.0；AGPL 可以用于商业场景，但对网络提供服务的源码提供义务需要法务/发布方式确认。
- EN↔ZH **语言包许可需单独确认**，不能只看服务代码许可后就宣布可商用。
- 官方社区截至 2025-04 表示没有 glossary 管理 API。因此它不能被宣称为“天然保证术语不变”的产品；是否达到项目所需的术语保真，只能以实际 query 的译文质量判断。

这些是 LibreTranslate 的能力与合规边界，不改变其作为“本地版 Google/Azure 式基础翻译服务”的正确定位。

## 5. 当前结论和后续动作

本轮不再把 Marian、OPUS-MT、BGE-M3 sparse、LLM 翻译、术语扩展或翻译模型训练列为候选路线。

**当前应选的服务级首要候选是 LibreTranslate。** 它不是因为底层引擎而被选中，而是因为它提供了与 NeuCLIR 所用 Google Translate API 同类的、可本地部署的翻译服务接口。

下一步仅剩两项同一层面的核验：

1. 核清 LibreTranslate 所安装的双向 EN↔ZH 语言包许可是否满足“免费、官方允许商用”。
2. 只看该服务对现有 Law 失败题 `q_raw` 的忠实翻译质量；不调用 LLM，也不训练任何东西。若它不达标，应继续寻找**服务级**离线替代品，而不是退回到翻译引擎/模型选型。

## 6. 官方资料

- [TREC 2024 NeuCLIR Overview](https://trec.nist.gov/pubs/trec33/papers/Overview_neuclir.pdf)：第 2.5 节说明 query translations 由 online Google Translate service 产生；第 2.7.2 节说明 `QGT` 以 machine-translated queries 检索原生文档。
- [LibreTranslate 官方文档](https://docs.libretranslate.com/)：self-hosted、本地启动与 `/translate` API；说明其定位为不依赖 Google/Azure 的开源翻译 API。
- [LibreTranslate 官方代码库与许可](https://github.com/LibreTranslate/LibreTranslate)：AGPL-3.0、完全 self-hosted API 的声明。
- [LibreTranslate glossary 社区答复](https://community.libretranslate.com/t/glossary-support/1796)：确认当时没有 glossary 管理 API。
- [Azure Translator Translate API](https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/reference/v3/translate)：Google/Azure 类翻译服务的另一参照；含单句/批量翻译以及动态词典接口。
