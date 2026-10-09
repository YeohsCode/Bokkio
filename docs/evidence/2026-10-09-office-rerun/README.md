# Office 题库重跑尝试 / Office benchmark rerun attempt

日期：2026-10-09；执行代码提交`4b6de28`。独立新工作区准备三道固定WindowsWorld L1原题，Word/Excel/PowerPoint每题15次动作预算。源内容/预算检查通过，初始输入的目标评分均不通过；初始化检查不是Agent成绩。

## 实际执行

运行`office_pilot.py run`，返回blocked：**planned 3 / started 0 / blocked 3**。Mac会话报告session_locked=true，AX/capture/events均true；桌面工具自动解锁失败。因此没有构造Agent/Planner/Jev，没有题目动作，也没有新增任务评分，三个score为null。原始VLM未调用，Windows未使用。

这不是新一轮0/3失败率；上次实际执行的0/3成绩保留为历史。本次不能评价新视觉接入的任务效果。该新工作区已有结果，不覆盖；后续使用另一个隔离工作区运行。

证据：[run.json](run.json)、[validation.json](validation.json)、[SHA256SUMS](SHA256SUMS)。原始Office文件/准备日志保留本地，不发布截图、完整桌面树或凭据。

## English

A fresh workspace prepared the three pinned WindowsWorld Office tasks with original 15-action budgets and failing setup targets. The actual runner returned planned 3, started 0, blocked 3 because the Mac input session is locked; all permission preflights pass, but automatic desktop unlock failed. No Agent model calls/actions or new task scores occurred. Scores remain null, distinct from the historical executed 0/3 result. Windows and original VLM judging were not used.
