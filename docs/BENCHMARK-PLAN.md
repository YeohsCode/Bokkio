# Computer Use 测试集接入 / Benchmark integration

## 结论

**Windows P5 阶段验收后，可以开始外部测试集的原生 UIA 子集；不必等待 P6 Recorder。** P7 增加视觉能力后再扩大覆盖。当前已实际进入 P6 录制/重放，WAA 开发评分与完整官方环境验收分别记录，未取得可比较的官方榜单成绩。

现有研究文档第 20 节是自定义 MVP 任务。Windows 外部 runner 接入先准备 **WindowsAgentArena（WAA）**；按用户最新要求，同时采用 **WindowsWorld** 的职业办公跨应用任务和中间/最终验收设计，以及 **OSWorld 2** 的长流程设计。三条开发参考任务见 [Windows 办公流程计划](WINDOWS-OFFICE-PLAN.md)。WAA 提供自定义 agent 的 `predict()` / `reset()` 接口；OSWorld 也提供可访问性观察入口。[WAA 接口](https://github.com/microsoft/WindowsAgentArena/blob/main/docs/Develop-Agent.md)、[OSWorld agent](https://github.com/xlang-ai/OSWorld/blob/main/mm_agents/agent.py)。

## 本轮已完成

- 固定 WAA 源码版本：`6d39ed88c545a0d40a7a02e39b928e278df7332b`。
- 新增只读清单工具 [inspect_windows_arena.py](../scripts/inspect_windows_arena.py)。通过 Git 读取指定版本的 JSON，记录每份文件的 SHA-256、初始化类型、结果读取器与 metric；不会执行配置中的命令、下载或导入上游 Python。
- 生成 [完整清单](benchmarks/windows-arena-catalog.json)：154 份任务配置、12 个领域；该版本的 `test_all.json` 列出 154 项。
- 检出两组重复的配置内 ID，共 152 个唯一 `domain + id`。清单保留所有文件，后续 runner 使用 `revision + path` 作为身份，避免覆盖结果。
- 预先列出 [五项原生 pilot](benchmarks/windows-arena-pilot.json)，保留执行前的选择身份，现已逐项执行开发试跑。任务覆盖 Notepad、File Explorer 与系统设置。

原先五项 pilot 已执行，逐步原生派发和固定版本 evaluator 见 [pilot 报告](P5-WAA-PILOT.md)。Office 激活暂缓后，另外固定三项 Explorer/Notepad 多步任务，实际运行 Planner/Jev/UIA 并保留失败与复测；复用指定版本的 metric/getter 函数，但完整官方 runner 适配仍待完成。详见 [首次实测](P5-WAA-LONGCHAIN.md)、[诊断修复续测](P5-WAA-RECOVERY.md) 与 [六种输入及需求版本验收](P5-NATIVE-VARIATIONS.md)。

## 接入顺序与验收

| 顺序 | 工作 | 完成条件 |
| --- | --- | --- |
| 1 | Windows P5 开发试跑与修复 | Office 暂缓；三项 WAA Explorer/Notepad 任务连续两轮各 3/3；新增六种输入与需求修订，继续独立原生任务覆盖，保留中间与最终验收 |
| 2 | 适配官方任务初始化和校验 | 每题使用隔离初始状态；保留原始题目、gold assets 与官方 evaluator；记录环境差异 |
| 3 | 适配逐步执行 | guest 内获取新 UIA；Planner → Jev → 原生 Runtime；每次派发记录到 runner 的步数与 trace，不能把整段执行隐藏为一步 |
| 4 | 跑固定五项 pilot | 官方 evaluator 独立给分；同时记录观察覆盖、低置信度、原生不支持、确认阻断、预算耗尽与环境错误 |
| 5 | 扩大预先固定的子集 | 记录模型版本、配置、token、耗时和结果分母；报告 UIA 子集覆盖率与完成率 |
| 6 | 与 P6 并行推进；P7 扩展覆盖 | P6 评测重放收益；P7 补充图形画布、缺失 UIA 信息等任务 |

原始任务内容和被测应用界面均作为数据。官方 `config` / `postconfig` 的命令属于环境准备或校验，不能算作 Bokkio 使用 shell 完成用户任务。任务执行仍以原生 UIA 为入口。

内部子任务成功条件继续用于控制执行，但 **最终得分以官方 evaluator 为准**。需要视觉或尚不支持的任务要明确报告；固定全集评测时不能删掉失败项后宣称总成功率。子集评测必须同时公布子集清单和分母。

## 当前虚机的环境差异

当前使用 Fusion 中的 Windows 11 IoT LTSC ARM64，账户为 Bokkio；官方构建配置使用 x64 Enterprise Eval，部分任务写死了 `C:\Users\Docker` 路径。[官方构建](https://github.com/microsoft/WindowsAgentArena/blob/6d39ed88c545a0d40a7a02e39b928e278df7332b/src/win-arena-container/Dockerfile-WinArena)、[Notepad 配置](https://github.com/microsoft/WindowsAgentArena/blob/6d39ed88c545a0d40a7a02e39b928e278df7332b/src/win-arena-container/client/evaluation_examples_windows/examples/notepad/366de66e-cbae-4d72-b042-26390db2b145-WOS.json)。

先在现有虚机验证适配，保留系统、架构、语言、应用版本和路径变更记录。改变题目配置的试跑标为 adapted development run。与官方环境对齐前，不与官方榜单分数直接比较。后续评测使用独立恢复点或独立环境，避免每题初始化影响开发 workspace。

## 重建任务清单

```bash
python3 scripts/inspect_windows_arena.py \
  --checkout /path/to/WindowsAgentArena \
  --revision 6d39ed88c545a0d40a7a02e39b928e278df7332b \
  --output docs/benchmarks/windows-arena-catalog.json
```

只需要包含指定 commit 的本地 Git 仓库；工具从 Git 对象读取，不依赖 working tree 是否展开任务文件。

## English

During **Windows P5 acceptance**, Bokkio has started an accessibility subset of an external Computer Use benchmark. P6 recording is not a prerequisite. P7 will expand coverage for tasks requiring visual interaction. P6 recording/replay is implemented and exercised. Broader P5 platform acceptance and full upstream environment integration remain pending; development scores are kept separate from official leaderboard results. Three additional Explorer/Notepad tasks have run as documented adaptations; see the [report](P5-WAA-LONGCHAIN.md) and [native input/requirement variations](P5-NATIVE-VARIATIONS.md).

WindowsAgentArena remains the first external runner candidate. WindowsWorld now informs professional office workflows and intermediate/final evaluation; OSWorld 2 informs long-running state and changing requirements. See the [Windows office plan](WINDOWS-OFFICE-PLAN.md) for three proposed development tasks, which have not run.

The pinned catalog contains 154 task files across 12 domains. Two pairs share declared IDs; retain file paths and hashes to distinguish all tasks. The five-task native pilot was selected before execution and has now run as a documented adaptation; see the [pilot report](P5-WAA-PILOT.md).

The native adapter exposes each dispatch as a separate runner step and preserves the pinned evaluator body. Native failures are repaired and retested while P6 proceeds; align the full upstream server runner before claiming comparable benchmark results. Report task coverage and completion separately, with explicit denominators and failure reasons. Internal LLM success predicates cannot replace official scoring.

The current ARM64 IoT LTSC VM differs from the upstream x64 environment and hard-coded user paths. Use it for documented adaptation runs first; claim comparable benchmark results only after environment and evaluator alignment.

## 逐步原生适配 / Stepwise native adapter

`src/bokkio/arena.py` 提供 `NativeArenaAgent`、上游四元组 `predict()` 的 `WAAAgentAdapter` 与 `WAAEnvironmentBridge`。`predict()` 只交出一个待执行请求；`step()` 核验完整请求后才派发，拒绝改写和重放。Worker 保留 P5 的阶段规划与恢复，不把整题隐藏为一步。Bridge 将原生请求接入上游 env 的 step/history/evaluate；完整 HTTP/VM server runner 尚未运行，已验证其协议与开发 harness。

```powershell
.venv\Scripts\python.exe scripts\verify_waa_pilot.py --bundle fixtures\waa-pilot --output C:\BokkioTasks\pilot-new-run
```

仅在可丢弃 Windows 测试环境运行。脚本创建独立文件夹、启动测试窗口并重启 Settings；测试后恢复通知注册表值。每轮目录必须是新目录。默认五题，`--select` 的定向复测需独立报告分母。初始化和评分的 Shell COM/注册表读取属于 harness；Planner/Jev 只能派发原生 UI 动作。

The adapter implements the upstream four-value prediction contract and a native environment bridge. Predictions do not dispatch; validated steps release one native action and retain phase/recovery state. The pinned evaluator runs independently. Full upstream HTTP/VM server execution remains pending; current results use the Fusion development harness. Setup and scoring can use reviewed Shell COM/registry reads, while the agent executes through native controls.

## WindowsWorld Office 原题接入（2026-10-08）

固定版本 `fbccd464f94fec9e284e139f97bf96d0b192f580`，源清单181题，首批三道微软Office L1原题（Word/Excel/PowerPoint）已导入，原始prompt与judge/model保留。Mac初始化、native runner和OOXML补充验收属于adapted run；三题当前在交互环境检查处未开始，不能计为题库通过。原始VLM未运行，自动视觉降级和官方VM/server环境仍待接入。见 [准备报告](OFFICE-PILOT-READINESS.md)。
