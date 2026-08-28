# W1 验证 A — 模型配置记录

记录日期：2026-06-25  
用途：W1 工具调用早期验证（verify_tools.py）两档量化对比依据

---

## qwen3:q4km（Q4_K_M）

| 字段 | 值 |
|------|-----|
| Ollama 模型名 | `qwen3:q4km` |
| 来源 | Ollama registry `qwen3-vl:8b-instruct-q4_K_M` |
| architecture | qwen3vl |
| parameters | 8.8B |
| quantization | Q4_K_M |
| embedding length | 4096 |
| Capabilities | completion / vision / tools |
| num_ctx | 8192 |
| temperature | 1 |
| top_k | 20 |
| top_p | 0.95 |
| num_predict | 512 |

Modelfile：`deploy/Modelfile.q4_k_m`

---

## qwen3:q5ks（Q5_K_S）

| 字段 | 值 |
|------|-----|
| Ollama 模型名 | `qwen3:q5ks` |
| 来源 | bartowski/Qwen_Qwen3-VL-8B-Instruct-GGUF（HuggingFace 社区量化，Qwen 官方 org 成员） |
| GGUF 文件 | `models/Qwen_Qwen3-VL-8B-Instruct-Q5_K_S.gguf` |
| architecture | qwen3vl |
| parameters | 8.2B |
| quantization | Q5_K_S |
| embedding length | 4096 |
| Capabilities | completion / vision / tools |
| num_ctx | 8192 |
| temperature | 1 |
| top_k | 20 |
| top_p | 0.95 |
| num_predict | 512 |

Modelfile：`deploy/Modelfile.q5_k_s`

---

## 参数对齐说明

- **num_ctx=8192**：RTX 5060 Ti（8151 MiB VRAM）。Q4 权重约 6.2 GB + KV cache 1.15 GB ≈ 7.35 GB；Q5 权重约 5.5 GB + mmproj 1.16 GB + KV cache 1.15 GB ≈ 7.81 GB（余量约 150 MiB）。~~两档均可完整驻留显存，但 Q5 余量更紧，不溢出 CPU~~——这句是纯算术推算，2026-07-15 真实测试（见下方"VLM 图片处理实测补充"）证明不成立：Q5 在真实 PDF 导入场景下稳定 OOM，不是"余量紧但够用"
- **temperature=1**：Qwen3 推荐工作区间上限，在最高随机性下通过即生产环境（temperature≤1）有保障
- **top_k=20 / top_p=0.95**：Qwen3 官方推荐采样参数
- **vision capability**：Q4 通过 Ollama registry 内置视觉编码器；Q5 通过单独下载 `mmproj-Qwen_Qwen3-VL-8B-Instruct-f16.gguf` 并在 Modelfile 中第二行 FROM 加载，两档均具备视觉能力。W1 验证不涉及图像输入，不影响工具调用测试结论

---

## W1 验证 A 结论（2026-06-25）

| 档位 | format | precision | specificity | tool_acc | p50 延迟 | p95 延迟 | 均值 token | 判定 |
|------|--------|-----------|-------------|----------|----------|----------|------------|------|
| Q4_K_M | 100% | 100% | 100% | 100% | 2.7s | 17.6s | 1332 | PASS |
| Q5_K_S | 100% | 90% | 100% | 100% | 3.6s | 16.6s | 1333 | PASS |

阈值：format≥95%  precision≥90%  specificity≥90%  tool_acc≥90%

**视觉检查备注：** check_vision.py 在工具调用测试完成后立即运行，此时 Q4 和 Q5 因 keep_alive=1200s 仍同时驻留显存，8 GB 显存不足以同时容纳两档模型 + 新推理请求，Ollama 触发换入换出导致延迟超过 60s 阈值。这是测试时序问题，视觉功能本身正常——两档视觉能力均已通过 `ollama show` 确认（Capabilities 含 vision）。~~单独运行时不会复现。~~——当时只是断言，没有补跑验证；2026-07-15 补跑了 `check_vision.py --models qwen3:q5ks` 单独运行，确认 PASS（见下方补充）。但这只证明"单独跑没问题"，不能推广到"真实导入场景没问题"，见下方补充里更完整的结论。

**默认量化：** Q4_K_M

**理由：** 两档均过线；Q4 precision=100% 优于 Q5 的 90%（Q5 ret-006、ret-008 未触发工具），Q4 p50 延迟更低（2.7s vs 3.6s），且 Q4 保留视觉能力备用。选 Q4_K_M 作为 W1 默认量化。

---

## num_ctx 后续实测补充（PR #15，2026-07-05）

`RealExecutor` 落地（PR #15）时对 num_ctx 做过更进一步的真实验证：**8192 确认可行，16384 确认不可行**（原始测试数据未留存，仅记录结论，避免后人误以为只有本文档最初记录的选型推算、没有后续真实验证）。`deploy/Modelfile.q4_k_m`/`Modelfile.q5_k_s` 维持 `num_ctx 8192` 不变；`pipeline/agent/client.py` 同批改为不再每次请求传参覆盖 `num_ctx`，交由 Modelfile 默认值控制（commit `aab8492`）。

---

## VLM 图片处理实测补充（2026-07-15）

W1 只验证了工具调用（文本），从没真实测过 Q5_K_S 在图片处理场景下的显存表现。2026-07-15 用真实图片/真实 PDF 补测，结论：**Q5_K_S 当聊天模型没问题，但当 VLM 图片理解模型用，在真实书籍导入场景下不可用。**

### 分场景实测结果

| 场景 | 是否经过 marker 解析 | 结果 |
|---|---|---|
| `check_vision.py --models qwen3:q5ks`（单独跑，合成测试图） | 否 | PASS，100% GPU resident，13.1s |
| 独立真实图片文件（`VLMImageParser`，`eval/testset/cs/raw/pic/` 3 张真实图，连续 4 次） | 否 | 4/4 成功，峰值显存 7275~7559MiB / 8151MiB，余量 590~876MiB，质量人工核对良好 |
| 真实 PDF 导入（`vm-paging.pdf`，6 张内嵌图，marker 解析→VLM 批量描述） | **是** | **0/6 成功**，全部 CUDA OOM，触发连续失败熔断 |

### 根因

前两种场景（无 marker）里 Q5_K_S 稳定可用；一旦是真实 PDF/EPUB 导入（marker 先跑一遍布局/OCR，紧接着 VLM 批量描述），Q5_K_S 加载稳定失败——不是偶发，是这次真实测试里 100% 复现（marker 处理完确认已正常释放显存回落到约 263MiB，不是 marker 残留占用）。日志显示每张失败的图耗时约 10.7s 才返回错误，跟显存曲线对上：Ollama 在这 10.7s 内部对同一张图重试了 3 次模型加载，每次都爬到约 7706MiB 后 CUDA OOM 崩溃，3 次徒劳后才把 500 错误吐给调用方——这正是用户反馈"反复横跳"现象的真实机制。

对照：Q4_K_M 在同样"marker 先跑、VLM 紧接着跑"的真实场景下峰值显存更低（约 7275~7278MiB，比 Q5_K_S 低约 380~430MiB），PR #26 的真实端到端测试（`docs/test-report-2026-07-06-vlm-figure-routing.md`）40 张真实图片 100% 成功，这次用户自己复测也确认"稳得很，基本不会跳"。

### 结论更新

- **`BOOKAGENT_MODEL`（聊天）**：Q5_K_S 可用，不受影响——对话链路不经过 marker
- **`VLM_MODEL`（导入时图片理解）**：Q5_K_S **不可用**，只要书里有内嵌图（绝大多数书都有），导入会在 VLM 阶段大量失败降级。**继续使用 Q4_K_M 作为 `VLM_MODEL`**，这一点不因本次补测而改变
- W1 当年"两档均可完整驻留显存"的结论只对"无 marker 干扰"的场景成立，不能推广到真实导入链路，上方两处已加删除线标注
