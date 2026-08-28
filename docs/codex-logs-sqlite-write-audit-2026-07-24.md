# Codex `logs_2.sqlite` TRACE 写盘审查与后续处置依据

日期：2026-07-24

## 结论

`/home/ismy/.codex/logs_2.sqlite` 确有 TRACE 主导的高频写入突发，主要与活跃的 SSE 响应和 app-server 消息处理相关；证据不足以表明它在空闲时也以恒定速率持续写盘。

已创建一个可逆的 SQLite trigger 来静默忽略**新连接**写入的 TRACE 日志。实测表明，当前正在运行的 Codex 写入连接没有立即采用新 trigger：其 `MAX(id)` 和 TRACE 行仍增长。因此，必须在后续重启写入进程/会话后，再按本文的采样步骤验证止血是否生效。当前不应宣称已经完成修复。

本次不重启 Codex、不删除日志、不执行 checkpoint，也不修改 `state_5.sqlite` 或其他状态库。

## 路径与版本

用户最初写作 `~1.codex/logs_2.sqlite`。实际存在的日志库为：

```text
/home/ismy/.codex/logs_2.sqlite
/home/ismy/.codex/logs_2.sqlite-wal
/home/ismy/.codex/logs_2.sqlite-shm
```

本机命令行版本：`codex-cli 0.146.0-alpha.3`。这已高于外部教程所提到的 `0.142.0`；因此不能把当前问题简单归因为“未升级旧 CLI”。当前日志 target 中存在 `codex_api::sse::responses` 和 `codex_app_server::outgoing_message`，与桌面/app-server 路径相关。

## 初始只读观测

数据库使用 `journal_mode=wal`。

| 指标 | 观测值 |
|---|---:|
| 主数据库大小 | 5,742,592 B（初测） |
| WAL 大小 | 4,367,232 B（初测） |
| 日志时间范围 | 11:37:39–14:55:44 |
| `logs` 总行数 | 4,038 |
| TRACE | 2,211（54.91%） |
| TRACE 估算文本量 | 约 1,433,463 B |
| 最近 10 分钟 | 1,506 行，其中 TRACE 886 |
| 最近 60 秒 | TRACE 294，约 4.9 条/秒 |
| 10 秒桶峰值 | 14:54:30：161 行、TRACE 104（16.1 行/秒） |

主要 TRACE target：

| target | TRACE 行数 |
|---|---:|
| `codex_api::sse::responses` | 880 |
| `codex_app_server::outgoing_message` | 671 |
| `world_state` | 175 |
| `message_processor` | 156 |

存在低活动分钟（分别仅 10、13、32、16 行），故准确描述是“随活跃调用/SSE 流量出现高频 churn”，而非“整段会话持续恒定高频”。只看 WAL 文件大小不足以判断写放大；应采样 `MAX(id)`。

## 已实施的在线拦截

确认 `logs.level` 为 `TEXT` 后，已在日志库创建可逆 trigger：

```sql
CREATE TRIGGER codex_block_trace_logs_insert_v1
BEFORE INSERT ON logs
WHEN NEW.level = 'TRACE'
BEGIN
  SELECT RAISE(IGNORE);
END;
```

选择只拦 TRACE，而不是拦截整个 `logs` 表：这样保留 INFO/DEBUG 的诊断价值，影响小于全表 trigger。

### trigger 验证结果

创建前基线：

| 指标 | 值 |
|---|---:|
| `MAX(id)` | 32,322 |
| TRACE 行数 | 2,292 |
| 总行数 | 4,164 |
| 主数据库大小 | 5,976,064 B |
| WAL 大小 | 4,367,232 B |
| WAL 中 `TRACE` 文本计数 | 1,064 |

创建后约 15 秒：

| 指标 | 值 |
|---|---:|
| `MAX(id)` | 32,495 |
| TRACE 行数 | 2,271 |
| 总行数 | 4,219 |
| 主数据库大小 | 6,156,288 B |
| WAL 大小 | 4,367,232 B |
| WAL 中 `TRACE` 文本计数 | 1,094 |
| `id > 32322` 的 TRACE/INFO/DEBUG | 72 / 48 / 53 |

TRACE 总数下降是日志 prune/滚动造成，不能据此判断止写；关键指标是新 `id`、WAL 内容与新插入的 level。

对一个**新 SQLite 连接**手工插入 TRACE 的前后计数不变，证明 trigger 已生效。当前 Codex 写入进程仍能插入 TRACE，表明它可能缓存/预编译了 INSERT statement，或在创建 trigger 前已建立了未刷新 schema 的会话。故“SQLite trigger 会即时作用于既有连接”不是本机已经证实的事实。

副作用：新连接尝试插入 TRACE 时会被静默忽略；INFO/DEBUG 仍会写入。未删除日志、未 checkpoint、未截断 WAL。

## 与外部教程的比较

参考：[《Codex 疯狂写盘自救指南》](https://zixungou.com/tutorials/codex-cli-disk-write-fix)。教程建议升级、以 `MAX(id)` 确认、可用 trigger 拦截、然后 checkpoint/truncate WAL。

| 教程步骤 | 本次状态 | 后续处理 |
|---|---|---|
| 升级 CLI 至 ≥0.142 | 已是 0.146.0-alpha.3 | 不为教程版本再次升级；关注桌面 App 更新 |
| TRACE 占比与 `MAX(id)` 检测 | 已完成 | 重启后再次采样 |
| 建 trigger 在线止血 | 已完成，仅拦 TRACE | 重启后确认现有写入流是否采用它 |
| 全表阻断 logs insert | 未采用 | 仅在 TRACE trigger 仍无效且接受丢弃全部诊断日志时考虑 |
| checkpoint/truncate WAL | 未做 | 确认无活跃写入后、经授权再做 |
| 删除 `logs_2.sqlite*` | 未做 | 不必要；仅作为日志空间回收的最后手段 |

教程提及桌面/app-server 路径在 CLI 升级后仍可能高频写入；本机观察与这一风险相符。该教程是外部社区资料，不应替代本机采样验证。

## 后续修复步骤（当前任务结束后）

1. 先完成当前工作并保留本次对话/工作区状态。
2. 重启 Codex 日志写入进程或会话。该操作可能中断当前会话；不要在未保存任务上下文时执行。
3. 重启后确认 trigger 仍存在：

   ```sql
   SELECT name, sql FROM sqlite_master
   WHERE type = 'trigger' AND name = 'codex_block_trace_logs_insert_v1';
   ```

4. 间隔 30–60 秒采样两次：

   ```sql
   SELECT MAX(id) FROM logs;
   SELECT COUNT(*) FROM logs WHERE level = 'TRACE';
   ```

   同时记录 `logs_2.sqlite-wal` 的大小和修改时间。理想结果是 TRACE 与 `MAX(id)` 不再因 TRACE 大幅增长；INFO/DEBUG 仍可能带来少量写入。

5. 若 TRACE 仍高频增长，先识别实际桌面 App/内嵌引擎版本，再考虑升级 App；若不能解决且接受失去全部诊断日志，可改为全表 `BEFORE INSERT ... RAISE(IGNORE)` trigger。
6. 确认没有活跃连接或在停止 Codex 后，先做 SQLite `.backup`，再由用户授权执行 `PRAGMA wal_checkpoint(TRUNCATE)` 回收 WAL 空间。
7. 官方修复后删除 trigger：

   ```sql
   DROP TRIGGER IF EXISTS codex_block_trace_logs_insert_v1;
   ```

## 安全边界

- 不删除或修改 `state_5.sqlite`、会话状态、记忆、goals、认证或配置文件。
- 不把日志库删除误认为“修复写入路径”；删除只回收旧空间。
- 未经明确授权，不重启当前 Codex 写入进程、不 checkpoint/truncate WAL、不改用全表日志拦截。
