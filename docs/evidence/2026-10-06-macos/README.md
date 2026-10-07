# Mac 原生测试证据 / Mac native evidence

日期：2026-10-06。仅自有 Cocoa fixture，原生 AX，按 PID 限定。原始 JSON/log 以确定性 gzip 保存；checksums.json 包含 52 个压缩文件字节哈希，validation.json 记录 8 份 Workflow、21 份检查点校验及最终源码匹配。

- preflight.json.gz：初始真实窗口/控件读取。
- scroll.json.gz：初次两个方向各三次往返，共 12 次确认动作。
- p5-v1/、p6-v1/：初始成功模型和 Workflow 轮次，保留其历史版本。
- controls-v1/：表格 select 在派发前拒绝；滚动通过，完整动作轮次未完成；已调用四次动作，但完整回执未归档。
- controls-v2/：角色修正后原生动作 3/3、双轴滚动通过。
- p5-v2/：最终代码三条真实模型任务 3/3；尝试数 4/4/5，成功 action 回执各 4；第三条旧快照拒绝后一次重规划。
- p6-v2/：最终录制 3/3、成功 trace 重放 3/3、结构重排 1/1、零派发失败和版本修复、暂停后只执行余下两步。
- host-tests.log.gz：293/293 主机隔离测试。

上述分母按独立轮次保留。没有 Office、浏览器 DOM 或截图路径。Mac 文件交付、跨执行进程恢复和视觉兜底仍待验收。详情见 [报告](../../MACOS-FOLLOWUP.md)。

## English

All runs are archived separately. Final native controls and model cross-app tasks pass 3/3. Final recorded and compiled workflows each replay 3/3. Actual control reorder, parent-linked repair and two-action resume pass. The first control run failed before selection dispatch; its incomplete action receipts are disclosed. Archive byte hashes, eight workflow hashes, 21 checkpoint hashes and final source hashes were verified. No credentials or personal data were found by the additional evidence-pattern scan.
