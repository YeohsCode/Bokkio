---
source_path: docs/evidence/2026-10-12-macos-completion/README.md
source_version: 0feda6de6e3d3b117a516ed48a5352574b438a29
ingested: 2026-10-13
sha256: d8df521b6a9a560e0ccd08f853c43afad9d2b2d950a50e2a9f50641b721cbac8
---

# macOS 测试加强执行报告

执行：2026-10-12～13；接续基线 575ed6f，Runtime 0.2.0。本机已完成 12 题 × 三调用方的 any-tool 主批、关键家族追加样本和延迟审批。产品成功率目标尚未达到；人工、客户环境和 Windows 验收继续单列。

## 自主业务结果

| 调用方 | 完整主批 | T03/T09/T11 三份样本 |
|---|---:|---:|
| 当前 Codex official MCP client bridge | 12/12 | 9/9 |
| 当前系统 Hermes | 8/12 | 4/9 |
| DeepSeek Harness SDK/native runtime | 6/12 | 4/9 |
| 合计 | 26/36 | 17/27 |

主批所有 36 项均实际启动，有逐题结果；覆盖 Finder、Numbers、TextEdit、隔离浏览器、Preview、Pages。两份追加稳定性输入为 7/9、5/9，与同一冻结源码主批的九份关键样本共同构成 17/27。不得把主批、追加和历史复测加总为一次成功率。每种调用方至少 10/12、关键家族三份全过的目标未满足。

主批见 [前六题](final-main-v31.json)、[另六题](final-remaining-v31.json)；稳定性见 [v32](stability-v32.json)、[v33](stability-v33.json)、[家族汇总](business-summary.json)。对应 frozen 文件保存执行时源码、任务、变体和预算；details 文件补充输入哈希、提供方报告的 token、审批与父子操作关联、失败层次。费用或不可获得的计数为 null，不估算；Core 请求次数不等于宿主脚本内部每项文件/API 动作。

主要失败：Hermes 多项业务与界面正确但 CLI exit 1；一份发票结果缺 TOTAL 标签，一份任务未产出文件。DeepSeek 多项超 40 回合；另有未检查 Finder、未真正筛选浏览器、报告负责人及截止日错误。文件正确不能替代界面、持久化或调用协议完成。没有提高 240/480 秒、40 回合、60 次 Core 写请求预算来补分。

当前 Codex 保留会话、编写评测器并通过官方 MCP stdio client bridge 执行；不称盲测、冷启动、Codex CLI 原生挂载或与两种 GLM 调用方公平排名。Hermes/DeepSeek 每题新 oneshot，使用既有 GLM 5.3 Flash 路由，统一 low 推理设置；DeepSeek 输出预算 4096。只给业务目标、资源和通用接口说明，没有给两者业务解法代码。具体本机版本见 [environment.json](environment.json)。

## 本轮实现修复及历史更正

- 通用 macOS 精确窗口遍历避免读取所有无关文档；先计算全部兄弟身份，再读取目标窗口，保持 scoped/full ref 一致，动作前后范围一致。没有加入软件业务分支。
- Pages 采用 RTF 渲染文本、绑定 PID/窗口的本地 OCR 和新进程重开判定，隐藏 RTF 注释不能冒充正文；本批已真实验证。
- DeepSeek 退出码 0 不代表 SDK 完成：必须 finish_reason=completed 且有最终响应。旧 r3 更正通过数 7→5，旧选取矩阵 9/12→7/12（DeepSeek 1/4）；原始分数不覆盖。见 r1～r4-sdk-terminal-correction.json 和[历史报告](../2026-10-12-business-eval/README.md)。
- 剩余六题初次结果 14/18、17 项启动，保留 [remaining-initial.json](remaining-initial.json)；后续统一 low 参数的新主批独立计分。

## 审批等待与恢复

[最新审批汇总](approval-wait-latest.json)：三调用方分别真实等待 30/90/300 秒，9/9 安全与恢复通过。pending 期间零派发；过时观察拒绝，300 秒申请到期后不沿用批准；新观察、新申请恢复。代码和其原生 SDK 子动作分别批准，CSV 与实际字段读回正确，未知完成为零。

这是提供精确安全代码的 Runtime/Harness 合同，由独立 fixture 管理员审阅自动批准，不能计作自主业务或真实人工审批。Hermes 恢复原 CLI 会话；DeepSeek 保持同一 SDK/native runtime 进程并恢复相同 session；重建 SDK 实例不等同会话恢复。

初批 3/9；其余六项因模板外层换行审阅及评测器空 jobs 表处理错误失败。修复后补测 6/6，初始结果不删除，见 [initial](approval-wait-initial.json)、[retest](approval-wait-retest.json)。脚本为 scripts/evaluate_approval_wait.py；不会访问真实业务文档或自动接受 OS 权限。

## GUI 与最终安全复核

[GUI 首批](gui-initial-v40.json)：18 个记录、7 项可确定的业务启动、10 个预检阻塞、1 个评分器错误，0 通过。该错误用例实际已启动但缺少完整终态记录，不能把它算未启动或通过。专属 PID 注册等待、截图／原生记录区分、Codex 完成信号修复后，[GUI 复测](gui-final-v41.json)全部 18 项实际启动，**0/18** 完整通过；每种调用方 0/6。预算、Core 和 GLM 路由未为 GUI 放宽，源哈希单列。

GUI 策略禁用 code/process/DOM；Chrome 使用独立测试 profile，原有 Finder 限定精确窗口，其他应用使用专属测试 PID。原生表格编辑、文档保存、状态提交和调用方预算仍有缺口。T07 有实际过滤成功的部分证据，但 CSV 未保存，仍为失败。T01 的 Finder-only 与 SHA256 清单要求缺少可行的 GUI 生成通道，不能将其失败解释为通用 GUI 能力差。Codex GUI 是本会话编写的有限原生控制流程，部分工作流提前停止；不得据此判定某软件完全不受支持，也不做调用方公平排名。

[MCP 图片交付](mcp-image-delivery.json)在独立安装包上通过：真实自有窗口 PNG 作为 ImageContent 交付，尺寸与 SHA 一致，structuredContent 不重复 base64。[GLM 直接图片初测](vision-probe-initial.json)为 2/3，未保存最终颜色文字，不能诊断第三项错误；[补充诊断](vision-probe-retest.json)保留回复，3/3，三种合成 PNG 均 HTTP 200。它证明本次提供方路由接受图片并完成简单判断，不证明业务 Harness 正确消费 MCP 图片。DSH 本批模型配置声明 input=[text]，真实 Harness 的图像消费仍未确认；不据 GUI 分数声称 GLM 不支持图片。

[调用方工具日志核对](caller-tool-channels.json)未发现直接执行非 Bokkio 工具的事件；Hermes 包装器内存在未知工具／错误路由请求，均报告错误。外层包装器错误不能单独证明每个内层调用都未执行，工具事件也不等于 OS 沙箱证明。[终态预算核对](budget-audit.json)确认计为通过的用例均未超限。轮询守卫可能观察到第一条超限请求／回合，不能声称原子硬上限；最终 runner 另加退出后核对，防止快速结束掩盖超限。内部宿主脚本每个动作仍不在计数范围。

最终串行验证：

- [主机回归](host-regression.json) **587/587**。此前与 GUI 并行时 584/585，输入锁安全拒绝一项；[初次争用](regression-contention-initial.json)保留，随后串行全部通过。
- [原生／SQLite／审计合同](final-audit.json) **9/9**。
- [窗口／作业矩阵](final-faults.json) **18/18**；此前 16/18 保留为历史。两项正向物理输入本次实际成功，未修改或绕过守卫。
- [八类 Core 合同](core-contract.json) **8/8**；不是所有异常的覆盖率，不包括真实锁屏或人工审批。
- [独立 wheel](wheel-final-summary.json)：锁定依赖、新 venv、包导入位于 checkout 外；原生、代码、Browser 各 **3/3**，MCP 23 工具、CLI、自动管理员审批、115 事件／36 逻辑操作及父子关联对账通过。wheel SHA 记录于报告，未进行外部发行。

[源码对照](source-comparison.json)确认主批及稳定性全套源码相同，Core 与 GUI／最终安装包一致。GUI 准备和最终评分器终态预算修订另行记录，不能将旧评分器哈希称为最新版。最终源码见 [final-source-files.json](final-source-files.json)。

## 仍需外部参与或后续修复

- 每调用方 10/12 和关键任务稳定性目标未达标；需要新开发修订和完整冻结复测，保留本轮成绩。
- 三种调用方真实人工审批、真实锁屏后解锁：未获得实际人工参与，不自动锁屏或将自动批准计作人工。
- 第二物理显示器/其他缩放、客户指定应用与可丢弃数据、客户部署，以及 Windows 当前 Runtime 实机验证仍待对应环境。
- Numbers 原生 .numbers 保存/关闭/重开仍为历史 **1/3**。本轮补测两项均未保存；名称编辑字段写入得到验证，工作表模型提交未确认。Save/Save As 目标 disabled，backend 在调用动作前拒绝，但 Core 保守地记录为 completion_unknown，未重发。详见[原始检查器诊断](numbers-persistence-initial-diagnostic.json)、[两项补测](numbers-persistence-retest.json)及[调用证据](numbers-persistence-actor-diagnostics.json)。需要修复通用禁用目标的零派发分类、验证编辑提交后重测；不能用 CSV 展示替代 .numbers 持久化。
- GUI T01 范围可行性、通用菜单／编辑提交、Harness 图片消费与正常终态仍需下一开发修订；每次改 Core/调用适配后按计划冻结并重跑受影响主批和三份稳定性，不覆盖本轮失败。

公共目录仅提交脱敏结果、哈希与环境版本；原始截图、SQLite、模型 trace 和 API key 留在本机私有目录。共享接续入口：[状态](../../progress/STATUS.md)、[工作包](../../progress/test-strengthening.json)、[跨平台接续](../../progress/HANDOFF.md)。
