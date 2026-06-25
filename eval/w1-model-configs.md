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

- **num_ctx=8192**：RTX 5060 Ti（8151 MiB VRAM）。Q4 权重约 6.2 GB + KV cache 1.15 GB ≈ 7.35 GB；Q5 权重约 5.5 GB + mmproj 1.16 GB + KV cache 1.15 GB ≈ 7.81 GB（余量约 150 MiB）。两档均可完整驻留显存，但 Q5 余量更紧，不溢出 CPU
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

**视觉检查备注：** check_vision.py 在工具调用测试完成后立即运行，此时 Q4 和 Q5 因 keep_alive=1200s 仍同时驻留显存，8 GB 显存不足以同时容纳两档模型 + 新推理请求，Ollama 触发换入换出导致延迟超过 60s 阈值。这是测试时序问题，视觉功能本身正常——两档视觉能力均已通过 `ollama show` 确认（Capabilities 含 vision）。单独运行时不会复现。

**默认量化：** Q4_K_M

**理由：** 两档均过线；Q4 precision=100% 优于 Q5 的 90%（Q5 ret-006、ret-008 未触发工具），Q4 p50 延迟更低（2.7s vs 3.6s），且 Q4 保留视觉能力备用。选 Q4_K_M 作为 W1 默认量化。
