# P5：15 次失败的诊断与修复

日期：2026-10-04（北京时间）。延续原先固定的三项 WAA Explorer/Notepad 任务。原先 15 次失败的证据保留在 [首次报告](P5-WAA-LONGCHAIN.md)；本报告记录后续诊断和复测。项目仍以原生 computer use 为主，Office 暂缓。

## 原先 15 次为什么失败

以下按每次尝试的**最后阻断**分类，合计 15；一次尝试可能出现多个中间错误，不能把分类当作独立根因的次数。

| 最后阻断 | 次数 | 已确认的原因 / 证据 |
| --- | ---: | --- |
| Planner 输出截断 | 3 | 第一轮 8,000 completion tokens 全被 reasoning 消耗，没有完整 JSON。low 档有改善，但 v7 后续阶段规划仍截断。 |
| UIA 查找超时 | 6 | `FindFirstBuildCache(ProcessId=...)`；部分先有错误字段写入。Runtime 每次读/动作重新从桌面发现同一进程，模态状态下不可靠。具体 provider 超时机制仍未完全证明。 |
| Jev 低置信度 | 5 | 搜索框重复包装和子节点都被标记 ambiguous，全部被排除，模型没有可写候选；另有菜单/保存字段的候选歧义。阈值保持 0.7。 |
| 原生验收不成立 | 1 | 多个文件行都有 Size，需要以父级文件名确定唯一字段；模型自称完成不足以证明结果。 |

另有两项直接探测发现：

- xa11y 会默认给 TextField/TextArea 暴露可写动作，即使 ValuePattern 不可用。某些文件行 Name **确实报告可写**，它对应重命名已有文件，不能拿来填写 Open/Save 的目标路径。
- Search Pictures 包装层和子节点对应同一原生 RuntimeId、同一矩形和可写 ValuePattern。结构重复不等于两个独立输入框。

## 已实施的改进

1. **实际原生能力。** 在所属 HWND 内，以 PID、控件类型、名称、类、AutomationId 和矩形匹配唯一原生元素，读取真实 ValuePattern。缺失或读取失败时不提供写入动作；写入前重核 RuntimeId 和只读状态。
2. **候选去重。** 同一窗口与 RuntimeId 的 set_value 候选只保留一个；歧义结构仅在原生身份已确认时允许该直接写入，其他动作仍受原有约束。File name 与 Name 的名称包含关系、ComboBox 与 Edit 重复写入也已处理。
3. **绑定进程后获取新快照。** Windows 数字 PID 复用 xa11y App 身份，避免反复桌面发现；继续通过 provider 获取新树，保留进程创建身份与失效检测。
4. **基于新资料分阶段规划。** 增加 continue_after_steps、独立阶段预算和阶段 trace。生成的阶段最多三步，在新对话框或正文出现后重新规划；只从已读数据推导输出。支持 present 条件核验对话框出现/关闭。旧计划和检查点仍可读取。
5. **动作候选与交付反馈。** 原生成功条件未成立时不向 Jev 提供 done；所需按钮已出现时排除无关展开操作，保留 0.7 置信度阈值。 最终文件不存在时不能因编辑器正文已写入而 completed；给 Planner 反馈缺少的目标路径，在原有重规划预算内补救。Gold 与评分结果继续只用于执行后的独立验收。CLI 提供可重复的 --require-file；要求写入 goal/checkpoint，恢复时不能省略这些要求。它核验文件存在，内容仍需要相应原生条件/独立验收。
6. **确定性词频。** 从当前原生 text_area 的已读正文计算用户指定单词的子串、区分大小写词频与不区分大小写词频。Planner 使用这些观察事实，避免把 22 次估成 13 次；没有读取 gold 或用文件 API 代替原生读入。
7. **文件对话框实际提交。** 独立对照确认：ValuePattern 字段回读已变，但保存仍请求覆盖 source.txt；切换焦点同样失败。原生 EM_SETSEL + EM_REPLACESEL 后正确保存 result.txt，正文为 22，输入字节保持不变。Runtime 只对所属经典 #32770 对话框中已验证可写的 Edit 使用这条路径，检查 HWND 父子关系、PID 与 RuntimeId，并以 5 秒 SendMessageTimeout 限制单次消息。其他控件继续使用 ValuePattern；trace 明确记录 write_source。增加原输入哈希保持验收，以及模态对话框禁用旧窗口时的动作阻断。
8. **明确隔离路径。** 原始指令保留；适配指令在输入文件和文件夹首次出现处直接替换为隔离绝对路径，避免选择个人 Documents 快捷入口。没有修改输入正文、预期答案或 metric。

GLM low 仍有预算不稳定，因此 v8 起的诊断/复测使用 Planner `openai/gpt-4.1`，Jev 保持 `typesafe/jev-1.13-20260917`。这是模型与 Runtime/规划改动共同作用的开发结果，不能单凭本轮证明某一改动的独立提升。

Win32 选择范围和替换操作依据微软 [EM_SETSEL](https://learn.microsoft.com/en-us/windows/win32/controls/em-setsel)、[EM_REPLACESEL](https://learn.microsoft.com/en-us/windows/win32/controls/em-replacesel)；编辑变更通过父窗口通知的机制见 [EN_CHANGE](https://learn.microsoft.com/en-us/windows/win32/controls/en-change)。文档支持 API 语义；本环境中的保存差异由上述对照实测证明。

## 后续轮次

**最后两轮各 3/3，连续 6 次端到端通过。** 三题都完成源读取、正文写入、Save As 路径与按钮证据、指定版本 metric=1、新进程重开、字节保持和输入文件哈希保持。计数输出为从原生正文计算的 22。目录绑定规则、输入与 metric 的基准版本保持一致；新目录下独立复测。

| 任务 | v14 动作 / 重规划 / 阶段续规划 | v15 动作 / 重规划 / 阶段续规划 | 最终验收 |
| --- | --- | --- | --- |
| png-list | 6 / 0 / 2 | 6 / 1 / 1 | metric=1；全部中间/最终检查通过 |
| size-report | 5 / 0 / 1 | 5 / 0 / 1 | metric=1；全部中间/最终检查通过 |
| word-count | 9 / 0 / 3 | 9 / 0 / 3 | metric=1；全部中间/最终检查通过 |

| Round | Finished / planned | Passed | Change |
| --- | ---: | ---: | --- |
| v6 | 3/3 | 0 | scoped ValuePattern read/write |
| v7 | 2/3 | 0 | phases and label/ComboBox fixes; interrupted |
| v8 | 3/3 | 0 | RuntimeId aliases, bound PID cache, GPT-4.1; overlap diagnostic |
| v9 | 3/3 | 0 | presence and missing-file feedback |
| v10 | 3/3 | 2 | bounded phases and concrete dialog examples |
| v11 | 3/3 | 1 | inline isolated input paths |
| v12 | 3/3 | 2 | deterministic native word facts and stricter presence schema |
| v13 | 3/3 | 2 | verified Win32 dialog edits and preserved input hashes |
| v14 | 3/3 | 3 | no done for unverified outcomes; unrelated expander pruning |
| v15 | 3/3 | 3 | repeat of v14 in fresh folders |

所有尝试均保留；v7 在第三题运行中被中断，保留 partial trace 和 interrupted.json，不当作完整三题成绩。v8 开始时与 v7 有短暂重叠，仅用作诊断；v9 起的验收轮次串行执行。

证据：[全部复测](evidence/2026-10-04-waa-recovery/)、[轮次索引](evidence/2026-10-04-waa-recovery/run-index.json)、[v14](evidence/2026-10-04-waa-recovery/waa-longchain-v14/summary.json)、[v15](evidence/2026-10-04-waa-recovery/waa-longchain-v15/summary.json)、[失败索引](evidence/2026-10-04-waa-recovery/failure-index.json)。原先 15 次失败仍在旧目录，未改写或删除。原始 trace、初始/重开快照保存为 gzip；交付文件保留为 deliverable.txt.gz，解压后的原始字节与 artifact_sha256 一致。

隔离回归 **macOS 152/152、Windows 152/152**。Windows 有一条 pytest 缓存目录写权限 warning，测试本身通过。最终六个核心模块的源文件哈希与 v14/v15 selection 一致，交付文件哈希及全部验收布尔值已复核，归档已做密钥模式扫描。两端 private Planner 配置已改为本轮验证的 GPT-4.1 / low，保留现有 API key；Jev 配置未变。

## 验收与后续计划

仍要求真实 Planner → Jev → UIA 定位/验证与原生 Windows 编辑消息、中间读取/写入/保存证据、固定版本 metric=1、文件存在、新 Notepad 进程重开及字节保持。脚本负责初始化和独立验收，agent 交付动作没有 shell、浏览器或直接文件写入代替。

已在同一三题取得完整通过并复测。下一步扩大原生 WAA 子集并适配完整官方 runner；继续补 P5 的需求变化、暂停恢复和产物版本，再进入 P6 Recorder/Workflow。Office 等可用微软许可证；macOS 保留对照验收。开发适配成绩不代表官方 benchmark 得分或通用桌面成功率。

## English summary

The original 15 failures ended in three truncated plans, six native UIA discovery timeouts, five low-confidence decisions and one unverified native outcome. These are terminal categories, not mutually independent root causes. Native probes confirmed unsupported advertised text writes and duplicate search representations sharing the same writable UIA RuntimeId. File-row Name can be writable, but serves renaming rather than dialog path entry.

A deterministic word-count fact is derived only from currently observed native editor text; the planner previously estimated 13 instead of 22. A separate native probe showed that dialog ValuePattern readback and focus changes did not commit the new filename. Verified Win32 edit messages persisted the requested output while preserving the source. The supplement is limited to writable Edit controls inside their observed classic dialogs, with identity/ownership checks and bounded message timeouts; write_source is recorded.

The changes verify ValuePattern capabilities and identities within the owning window, deduplicate native write aliases, reuse bound process identities while taking fresh snapshots, and plan bounded phases after newly opened dialogs or loaded text. A final delivery callback blocks premature completion and feeds missing-file evidence into recovery without revealing gold answers. Isolated source paths now appear directly in the adapted instruction. Recovery runs use GPT-4.1 for planning with the same Jev model; the combined changes do not isolate model effects.

The final two serial rounds each passed all three tasks (6/6): PNG file names, a size-filtered report and a persisted count of 22. Native intermediate checks, pinned metrics, input hashes, byte preservation and fresh-process reopening all passed. Both platforms passed 152 isolated tests; Windows reported one cache-permission warning. The two private Planner configurations now use the verified GPT-4.1/low setting with existing keys retained. Jev is unchanged.

Interrupted and overlapping diagnostics remain separate from serial acceptance runs. Full acceptance requires native intermediate evidence, the pinned metric, persisted artifacts and independent reopening. Native completion remains runtime-owned: unverified subtasks do not offer done, and visible invocation targets remove unrelated expansion candidates without lowering the 0.7 threshold. The CLI exposes --require-file and binds these requirements to the checkpoint goal.

Bokkio remains in P5 acceptance; Office activation, macOS comparison and the full official benchmark adapter remain pending.
