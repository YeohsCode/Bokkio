# P6 closure evidence / P6 闭合证据

2026-10-05，Windows 11 IoT LTSC ARM64 / x64 Python 3.12.13。实际原生 UIA 验收，所有桌面 actor 顺序执行。

| 轮次 | 状态与分母 |
|---|---|
| closure v1 | 基线准备中断，Windows path 参数样例校验失败；参数化正式用例未开始；一次基线选择调用未独立归档回执 |
| closure v2 | 基线 Notepad 保存与两次客户端选择回执通过；alpha 参数用例 s1 父节点不匹配，0 派发失败；另两组与扩展项未开始 |
| closure v3 | 两次客户端回执；同一七步模板三组参数 3/3；重启/跨进程恢复 1/1，仅新派发 1 步；无名容器恢复 1/1；真实 GPT-4.1 修复 1/1 |
| core v5 | 最终源码六步录制重放 3/3，五步真实 Notepad trace 保存/重开 3/3；错误 selector 0 派发，revision 2 修复通过 |

每轮 summary 保留计划、实际分母、错误与源码哈希。最终 closure v3 / core v5 的八个共用源码模块哈希一致且匹配当前源码，两份 verifier 的哈希分别保留。最终独立测试补充 Windows path 样例回归后，主机和 Windows 各 292/292；之前的 285/287/291 项日志保留原结果。

- `p6-complete-v3/report-workflow.json`：唯一参数模板；三个 run 的 `workflow_sha256` 相同。
- `paused.json.gz` / `resumed.json.gz`：不同执行进程与 Notepad PID，完成步骤保留，剩余派发一项。
- `wrapper-*.json*`：实际无名 Panel 变化；解析 lane 为 `named_context`。
- `model-*.json*`：失败、修复与重放；模型调用、usage 和 parent hash 保留。重放不调用模型。
- `p6-v5/`：最终六步/五步重放、录制与失败/修复版本。
- `inputs/`：原始 P5 v16 成功 trace 字节；SHA-256 与两份最终 summary 对应。
- `logs/`：部署、build、隔离测试、原生执行及退出码；临时用户路径规范化为 `C:/BokkioTestTemp`。
- `checksums.json`：91 份归档字节哈希。大 JSON/日志使用确定性 gzip；JSON 规范化为 UTF-8/LF，产物保留原字节。
- `validation.json`：11 个 Workflow 内容哈希、19 个检查点内容哈希、14 份文本产物及最终源码核验。

[P6 验收](../../P6-CLOSURE.md) 对照原始六项退出标准；[P7 计划](../../P7-PLAN.md) 列下一阶段。

English: Final native closure passed all parameter, process-resume, wrapper-change and real model-repair checks. Final core v5 separately passed three unchanged recording replays and three successful-trace save/reopen replays. Earlier failures and unstarted cases remain separate. Raw input bytes, output artifacts, native receipts, versioned repairs, checkpoints, source hashes and test logs are archived. Final source hashes match; both test hosts pass 292 tests. These are development acceptance results rather than official benchmark scores.
