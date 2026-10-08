# Office pilot preparation and blocked-run evidence

2026-10-08。Three pinned original WindowsWorld Microsoft Office tasks, Mac adaptation.

- `prepared.json`：隔离初始化、源文件哈希、schema/HTML QA；初始化文件不是执行结果。
- `setup-inputs/`：本次生成的合成 Word/Excel 和空白 PowerPoint 文件及 HTML 预览；PPT 目标结果文件不存在。
- `run.json`：planned 3、started 0、blocked 3，score null；输入会话锁定，未运行模型或 Office 编辑。
- `baseline-evaluation.json`：初始化负例 0/3 达标，不能当作 Agent 失败率。
- `host-tests.log` / `windows-tests.log`：两端各 373/373；评分正确/错误样式、内容保持、原始检查完整、输入篡改和环境阻断有隔离验收。
- `pid-event-probe.json`：单次自有应用进程定向事件实验没有业务变化，没有当作成功输入，没有更改生产守卫。
- `initialization-failure.json`：初次列宽命令失败及修正摘要。
- `source-hashes.json` / `checksums.json`：执行代码和证据字节版本。

不包含真实账户、凭证、无关窗口或业务文档。原始任务和 judge 参考见 [题目包](../../../fixtures/windowsworld-office/README.md)。详情见 [准备报告](../../OFFICE-PILOT-READINESS.md)。

## English

The software preparation/scoring pipeline is implemented; this archive proves a blocked preflight, not successful Office execution. All three original tasks are unstarted and scores are null. Initial inputs fail the target checks, and simulated evaluator tests are separate from task performance. No task editing/model call, outgoing mail or security-policy change occurred.
