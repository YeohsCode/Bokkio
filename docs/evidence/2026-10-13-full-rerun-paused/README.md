# Computer Use 完整复测：用户暂停

日期：2026-10-13；基线 f6e2c6c。计划主批 36、GUI 18、追加稳定性 18，共 72 次。用户暂停后，已向本批执行器及其测试子进程发送 SIGTERM，没有关闭无关应用。未修改产品、调用适配器、评分器或既有动作流程，失败未修复、未补跑。

暂停前主批已记录 12 项：4 通过、2 失败、6 预检阻塞。均为 Codex 已有 MCP 流程重放，不是新的自主模型解题。Hermes 正在执行的尝试被中断，尚无完整评分，不能当成通过或模型失败。GUI 和追加批次尚未开始；本报告不能代表完整矩阵成功率。

逐项结果：[partial-main.json](partial-main.json)。执行冻结：[main-frozen.json](main-frozen.json)、[run-manifest.json](run-manifest.json)。原始 trace、SQLite、应用截图和私有模型配置仅保留本机。
