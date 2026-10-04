# P5：原生输入变化、恢复与需求版本

日期：2026-10-04。延续 [WAA 三题修复](P5-WAA-RECOVERY.md)，重点仍是 Windows 原生 computer use。Office 激活与办公流程按用户要求暂缓。

## 本轮范围

预先固定六种新输入，每种只初始化源文件，由真实 GPT-4.1 Planner → Jev → UIA 完成交付。每项计划在正文写入后通过 control hook 暂停，保存检查点；新 Runtime 实例恢复后完成 Save As，并独立验证文件内容、源文件哈希和新 Notepad 进程重开。Oracle 在执行前确定，只用于执行后的评分；执行循环只反馈目标文件存在与否。

| Variant | 输入变化 | 独立预期 |
| --- | --- | --- |
| png-spaces | 空格、大小写 PNG 扩展名、`ignore.png.txt` 干扰项及 JPG/TXT | 三个真实 PNG 文件名，保持实际扩展名大小写 |
| png-many | 十个 PNG 和两个干扰文件 | 十个完整文件名，无重复或额外行 |
| size-boundary | 4、5、6 MiB 与小文件 | 仅 6 MiB 文件；严格排除 5 MiB |
| size-many | 三个大于 5 MiB 的文件及一个小文件 | 三个完整文件名 |
| count-punctuation | 标点、大小写、复数和单词内部子串 | 全词、不区分大小写：7 |
| count-zero | 只有复数和内部子串 | 全词、不区分大小写：0 |

这些是从 WAA 任务派生的自定义稳定性输入。原始任务、资产和 metric 仍校验固定版本哈希；新输入不套用原始 gold，`pinned_metric_score=null`。本轮不代表新增官方 WAA 任务成绩。

## 新发现与修复

1. **隐藏扩展名误判。** 首次 PNG 用例把原生显示的 `ignore.png` 当成 PNG，实际是 `ignore.png.txt`；真实 PNG 扩展名被隐藏而漏选。现在先用原生 View / Show 显示文件扩展名，再读取完整名称；提示词禁止仅由隐藏扩展名的显示文本判断类型。原生输入观察验收也修正为只隐藏最后一个后缀，不对显示名再剥一次后缀。
2. **匿名祖先导致按钮被排除。** Explorer View 被祖先的重复结构标记为 ambiguous，虽然按钮支持 ExpandCollapsePattern，候选被全部排除。现在对这类交互目标在所属 HWND 内核对 PID、类型、名称、类、AutomationId 和矩形，读取 RuntimeId 与真实 Invoke/Toggle/ExpandCollapse/SelectionItem 能力。执行前再次核对 RuntimeId、启用状态和 Pattern；只对已验证的动作走直接 UIA 调用，不放开其他歧义操作。相同原生身份的动作候选去重，trace 保存 action_source。Planner 观察也只展示循环可用的动作。
3. **保存后使用旧标题。** 一次大小报告确实保存且内容正确，但用旧 Notepad 标题检查对话框关闭失败，重规划再次保存而进入覆盖提示。现在 dialog 的 presence 检查强制 `window=null`，在动作前拒绝此类计划。初次、阶段、动作恢复和交付恢复的计划校验统一进入有界重规划。
4. **菜单勾选状态和到达路径。** xa11y 给 ToggleMenuFlyoutItem 提供了 toggle 动作，却返回 checked=null。现补读取真实 TogglePattern 状态；菜单关闭后的条件若误匹配文件行 Name 而丢失父菜单，候选为空时只对同一原生范围恢复一次完整候选，保留全部身份、能力和置信度约束。改变文件可见信息后先结束阶段、重读，再计算输出。v5 的 PNG 初始化会通过原生 UI 核验扩展名关闭，确保实际开启动作被测试。
5. **不可能同时满足的换行条件。** 多行大小清单被要求同时等于 LF 和 CRLF 正文，导致目标低置信度。现在拒绝同一目标/字段要求不同值的 AND 条件；text_area 正文比较统一 CRLF/LF。增加原生 checked 成功条件，兼容原生 on/off 读值。
6. **同名源文件与历史目录。** 需求变更 v1 打开了旧目录里的同名 `largefile.txt`，交付了 0，独立验收拒绝；应得到 7。新增可重复的 `--require-source`：在原生 Open 前核验 File name 的完整路径、唯一原生身份和 ValuePattern 读值；打开后要求唯一正文与源标题，记录当前需求版本的 source_acquired 和原生词频事实。源未读取时禁止写正文和完成；新需求必须重新读取，旧版本的源收据不能满足它。目前限于英文 Windows 经典 Open 对话框，其他应用需另行适配。
7. **菜单导航与阶段边界。** v5 的 png-spaces 展开 View 后，按 View 名称收窄丢掉了 Popup 内的 Show；保留当前 Popup 的原生菜单候选。真实勾选动作改变树后，强制重读并消耗阶段预算重新规划，避免继续使用隐藏扩展名下生成的旧文件清单。若 checked 状态已符合要求，但计划指定了错误父级，动作前拒绝再次切换，返回明确错误供重规划修正 parent_name。
8. **菜单生命周期与循环。** v7 的 checked=true 和 Show expanded=false 两个条件无法在原生子菜单销毁后同时读回。计划校验要求先读取勾选状态、再用独立步骤关闭菜单；每个子任务保存已读原生状态摘要，至少两次动作后回到先前未满足状态便触发有界重规划，避免耗尽全部动作预算。
9. **同名 Open 确认按钮。** 经典 Open 对话框的三个下拉箭头也叫 Open，导致真实确认按钮低置信度。仅在目标明确为 Open/Save button，且当前 Windows 经典对话框内观察到唯一同名直接子按钮时，排除同名组合框箭头的 click 候选；其他候选、原生身份/能力检查和置信度门槛保留。多个直接按钮或其他 provider 不应用此收窄。
10. **事实来源。** 当前原生编辑器的词频事实记录正文 UTF-8 SHA-256、字符数、窗口与父级；这些标识原生读值，不能当作源文件的字节哈希。文件源哈希由独立验收核对。

## 需求变更与交付版本

`DesktopAgent.run(..., resume=..., amend_reason=...)` 与 CLI `--amend-reason` 支持从暂停或已完成的检查点显式更改目标。需要新目标和非空理由；应用白名单必须保持一致，累计动作、重规划和阶段预算保留。普通恢复仍要求原目标一致。

检查点保存 requirements、goal_revision 和 requirement_amended 事件。新需求重读当前原生状态并重新规划；旧步骤保留在历史中，完成记录仅属于原需求版本。`--require-file` 验证后的 artifact_versions 记录路径、字节数和 SHA-256，重复验证同一版本不会增加重复记录。文件存在和哈希仅证明当时的交付字节，业务正确性仍需任务自己的验收。

原生需求变更用例先将上述文本的不区分大小写计数保存为 count-v1.txt，再显式改为区分大小写，重新通过 Notepad 打开原文，将新结果保存为 count-v2.txt。两个需求分别检查源读取、正文、保存对话框、路径、Save 按钮、独立计数与新进程重开；第二个需求还核对旧文件和旧历史不变。

## 运行记录

结果和全部失败归档在 [本轮证据目录](evidence/2026-10-04-native-variations/run-index.json)。完整 v5 通过 5/6；随后预选 png-spaces、count-punctuation、count-zero 三项的 v6 全部通过 3/3。六种变体各自已有通过记录，但它们来自不同源码版本与轮次，不能称为同一版本整轮 6/6。需求变更 v2 两个版本全部通过 2/2；累计 18 个动作、1 次重规划，约 364 秒。v7 菜单父级保护复测未通过，32 动作预算耗尽；勾选可见状态与关闭子菜单被错误设成同一步 AND 条件，展开/收起循环。现要求分步验收，并对重复原生状态提前进入有界恢复。v8 PNG 通过 1/1：10 动作、0 重规划。需求变更 v3 首版本因四个同名 Open 按钮的目标置信度不足被拒绝，第二版未开始；修复后 v4 两个版本全部通过 2/2，约 401 秒；macOS / Windows 隔离测试各 195 项通过。最后需求变更 v4 的六个模块哈希与发布源码一致。

v1 在动作前因测试脚本延迟导入导致 source_hashes 查找 KeyError，0 个任务开始；初始化失败日志保留。修正为显式导入待记录模块。v2 完成六项、通过 2/6，暴露上述隐藏扩展名、旧标题和多行条件问题；v3 完成六项、通过 3/6，保留 View 动作被排除的失败。v4 完成 1/6、通过 0/1；第二项在 29 次动作后中断，另四项未开始。View/Show 的原生展开已成功，剩余阻断是菜单勾选值缺失，导致反复切换；保存部分 trace 和独立 interrupted.json。v5 完成六项、通过 5/6；剩余 png-spaces 菜单导航失败触发上述修复。需求变更 v1 计划两个版本，仅首版本开始且未通过，第二版本未开始；错误文件内容 0 的证据保留。

| 运行 | 完成 / 预选 | 通过 | 说明 |
| --- | --- | --- | --- |
| variations v1 | 0 / 6 | 未评分 | 脚本初始化失败，未开始任务 |
| variations v2 | 6 / 6 | 2 / 6 | 隐藏后缀、旧标题、矛盾条件 |
| variations v3 | 6 / 6 | 3 / 6 | View 身份能力被过滤 |
| variations v4 | 1 / 6 | 0 / 1 | 第二项 29 动作后中断；四项未开始 |
| variations v5 | 6 / 6 | 5 / 6 | PNG Popup 导航仍失败 |
| variations v6 | 3 / 3 | 3 / 3 | 修复 PNG；两个计数启用源路径约束 |
| variations v7 | 1 / 1 | 0 / 1 | checked 与菜单关闭条件冲突，循环耗尽预算 |
| variations v8 | 1 / 1 | 1 / 1 | 菜单条件分步验收，10 动作、0 重规划 |
| requirement-change v1 | 1 / 2 | 0 / 1 | 错误目录同名原文，第二版本未开始 |
| requirement-change v2 | 2 / 2 | 2 / 2 | 正确交付 7 → 5，保留两版与旧历史 |
| requirement-change v3 | 1 / 2 | 0 / 1 | 同名 Open 下拉箭头分散置信度，第二版未开始 |
| requirement-change v4 | 2 / 2 | 2 / 2 | 最终源码交付两版，恢复过期快照和旧窗口标题 |

版本修订 v2 的第二行 `actions=18`、`replans=1` 是累计预算，首版本为 9 动作、0 重规划；不应将两行相加。两次 source_acquired 均属于各自需求版本，路径指向本次指定原文，正文事实为 insensitive=7、sensitive=5。两版 SHA-256 分别为 `7902699b…b2451`、`ef2d127d…afe39d`。

最终 v4 累计预算计数为 19、重规划为 2；其中一次过期尝试在派发前拒绝，trace 中成功的原生 action 事件为 18。源读取、独立内容、原文与旧文件保持、两版哈希、旧历史前缀及新进程重开全部通过；见 [最终核验](evidence/2026-10-04-native-variations/final-verification.json)。

## 复现

```powershell
.venv\Scripts\python.exe scripts\verify_waa_longchain.py `
  --bundle C:\BokkioWorkspace\longchain-bundle `
  --output C:\BokkioTasks\new-variations `
  --variants png-spaces png-many size-boundary size-many count-punctuation count-zero `
  --pause-before-save --hidden-extensions

.venv\Scripts\python.exe scripts\verify_p5_requirement_change.py `
  --output C:\BokkioTasks\new-requirement-change
```

使用新的输出目录。真实原生 runner 串行运行，初始化与独立验收不参与 agent 的交付动作。仅关闭本次启动的 Notepad 进程和 Explorer HWND。

原生 v6 的 PNG 用例耗时约 516 秒，两个计数用例约 152/172 秒，包含初始化、暂停恢复与重开。执行耗时仍高；后续细分原生 provider 读取、规划、决策与落盘耗时，再优化；这些总耗时不能直接作为模型延迟。

## 后续

仍处于 P5 验收。继续扩大独立原生任务，接入官方初始化、逐步 agent 接口与 evaluator，执行原先五项 pilot 后再进入 P6 Recorder/Workflow。跨平台 macOS 对照和真正 VirtualizedItem provider 覆盖保留待办；Office 等待可用微软许可证。

## English summary

Six fixed robustness fixtures vary names, file counts, mixed extensions, strict 5 MiB filtering, punctuation, case and substring counts. Each uses the real Planner/Jev/native loop, pauses after editor input, resumes with a new runtime, saves and independently reopens the deliverable. Custom inputs use separate post-run oracles, not the pinned WAA gold; these are development checks, not official benchmark scores.

The runs exposed hidden-extension misclassification, ancestor ambiguity excluding Explorer View, stale window titles after saving, and contradictory LF/CRLF predicates. Fixes show native extensions before classification, verify native action capabilities and RuntimeIds in the owning HWND, reject title-bound dialog presence checks before acting, and apply bounded plan repair at every planning boundary. Editor line endings are compared consistently and checked state is supported. Native text facts include a digest of the observed editor value and its character count. Current Popup menu candidates survive narrowing, and a verified native toggle forces a fresh planning phase. Required sources must be opened using their full paths in an English classic Windows Open dialog; native acquisition receipts and word facts are scoped to each goal revision. Output writes and completion are blocked until acquisition is observed.

Explicit requirement amendments retain the app allowlist, cumulative budgets, historical steps and prior deliveries. A new goal revision starts with fresh observations and planning; old receipts cannot satisfy it. Verified required files record byte counts and digests in artifact_versions. A separate native test changes the count from case-insensitive to case-sensitive, saves a new output and verifies both versions while preserving the source.

The initial harness failed before task execution; v2 passed 2/6 and v3 passed 3/6. Every attempted task and initialization failure is retained. v4 finished one task (0/1), interrupted the second after 29 actions and did not start the remaining four. Native View/Show expansion worked; missing menu checked state caused repeated toggling. Partial traces and an explicit interruption record are preserved. v5 passed 5/6. The first requirement-change run opened a same-name file from a remembered directory and saved 0 instead of 7; independent checks rejected it, and the second version did not start. Full-path source constraints address this failure. v6 retried three preselected fixtures (png-spaces, punctuation and zero count) and passed 3/3. Each of the six fixtures now has a passing attempt across rounds; this does not constitute a single 6/6 run on one code version. Requirement-change v2 passed both versions (2/2), delivering 7 then 5 while preserving the original output, prior events, source bytes and two artifact hashes. Its 18 actions and one replan are cumulative across revisions. v7 exhausted its 32-action budget after an invalid AND condition combined menu checked state with closed-submenu state. Checked readback and closure now require separate subtasks; repeated native states trigger bounded repair. v8 PNG passed 1/1 with 10 actions and no replans. Requirement-change v3 stopped after the first version because three combo arrows named Open competed with the dialog confirmation button. When an explicit Open/Save button intent has exactly one matching direct child of an observed classic native dialog, same-named combo arrows are excluded from its click candidates; all identity, capability and confidence checks remain. Final requirement-change v4 passed 2/2 in about 401 seconds. Host and Windows isolated tests each pass 195 checks. Its six module hashes match the published source. P5 acceptance, the full benchmark adapter, the original pilot and macOS comparison remain ahead of P6.
