# P6 native workflow evidence / 原生工作流证据

2026-10-05，Windows 11 IoT LTSC ARM64 / x64 Python 3.12.13。仅原生辅助功能操作，无浏览器或 DOM。

| 轮次 | 同一录制 JSON 重放 | 成功 Agent trace 重放 | 失败选择器 / 修复 |
|---|---|---|---|
| v1 | 未开始 | 未开始 | 打包预检缺少 trace 样例；0 原生启动 |
| v2 | 3/3；每轮六步、三个独立状态检查 | 3/3；每轮五步、16 字节与新进程重开检查 | 0 派发失败；revision 2 通过 |
| v3（定向确认） | 1/1；六步与全部独立检查通过 | 1/1；五步、字节及重开通过 | 0 派发失败；revision 2 通过 |
| v4（最终代码） | 3/3；每轮六步、六次上下文恢复与全部独立检查通过 | 3/3；每轮五步、16 字节及新进程重开通过 | 0 派发失败；revision 2 通过 |

- `p6-v2/summary.json`、`p6-v3/summary.json`、`p6-v4/summary.json`：真实分母、独立检查、执行源码哈希。
- 各轮包含录制、成功/失败/修复 Workflow、逐步重放、观察与回执。
- `inputs/` 保留真实 v14 / v16 Notepad trace 原始字节；SHA 与相应 summary 一致。
- `logs/` 保留失败预检与实际执行日志。测试临时目录规范化为 `C:/BokkioTestTemp`。
- `checksums.json` 校验归档文件字节。大型 JSON 与日志使用 gzip，解压后读取。

v2 后增加空字段 type 限制、invoke 能力别名与原生边界读取修复，因此不把 v2 的三次重复宣称为最终源码的三次重复；v3 单独保留。后续 checked 歧义恢复与录制无效果验收修复改变 agent/workflow，v4 在六个最终执行源码哈希上重新完成三次录制与三次 trace 重放。两端各 265 项回归通过，日志见 `logs/p6-v4-tests.log.gz`。

English: These are native development checks, with explicit denominators for each source revision. The recorder spans an owned WinForms fixture and Notepad; the compiled trace saves a real Notepad artifact. Replays use fresh processes and rebound app aliases, without models. Broken selectors fail before dispatch, while repaired versions preserve the original and its parent hash. Raw input traces, per-step receipts and independently verified outcomes are retained. Global human input capture and broader P6 workflows remain separate follow-up work.
