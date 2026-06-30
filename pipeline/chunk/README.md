# Chunker 设计说明

## token 上限与 overlap 的关系

`_MAX_TOKENS`（512）只约束每个 chunk 里**新增**的缓冲内容（`buf_tok` 的累计值），不包含 overlap 前缀。

`flush()` 写入 `Chunk.content` 时实际拼接的是 `overlap_text + 缓冲区内容`。`overlap_text` 是从上一个 chunk 结尾复制来的重复片段，最多 `_OVERLAP_TOKENS`（50）个 token。因此单个 chunk 最终的 `token_count` 实际上限是 `_MAX_TOKENS + _OVERLAP_TOKENS`（562），不是 512。

**为什么不把 overlap 计入 512 上限：** overlap 的目的是避免相邻两个 chunk 在语义边界处硬切断上下文，它是从上一个 chunk"借"来的重复内容，不是这个 chunk 独有的新信息。如果把它也计入硬上限，意味着每个 chunk 实际能容纳的新内容会缩水到 `max_tokens - overlap_tokens`（462），而这个缩水对所有 chunk 一视同仁——包括那些 overlap 为空的 chunk（比如紧跟在 heading/atomic 边界之后的第一个 chunk）。

这个权衡只在“长元素按句子边界切分”那条路径里被显式处理过：切分目标用的是 `max_tokens - overlap_tokens`，预留了 overlap 的空间。常规的缓冲区累积路径（判断 `buf_tok + elem_tok > max_tokens` 是否需要 flush）没有为即将追加的 overlap 预留余量——这是两条路径不一致的地方，目前未改动。

**下游使用注意：** 任何假设“每个 chunk ≤ 512 token”的下游逻辑（embedding 模型输入截断、检索结果长度预算等）需要按 `max_tokens + overlap_tokens` 留余量，不能按 512 硬编码。目前没有测试断言 `token_count <= max_tokens`，因为这个断言本来就不成立；后续如果要补测试，应断言 `token_count <= max_tokens + overlap_tokens`。