# Runtime 续测与 P4 接口（2026-10-02）

Windows 原生操作的四个缺口已收敛；Jev 接口与执行保护已实现。本文保留当时的 Runtime 和脚本化接口验证记录。随后真实 OpenRouter Jev 的五任务、四类难例与规模评测已运行，最新配置、契约和结果见 [P4 报告](P4-REPORT.md)。项目继续以原生桌面 Computer Use 为重点。

## 实现与真实验证

| 项目 | 结果 |
|---|---|
| Windows 方向滚动 | 使用 UIA ScrollPattern 的容器百分比，三轮横纵往返通过；到边界返回 unconfirmed |
| 滚动结果 | 同时检查位置与内容相对容器的坐标、可见状态或内容 ref 变化；排除滚动条子树 |
| 空文本 | 通过原生 ValuePattern 读取空字符串；失败保留未知值和错误，不把 null 推断为空 |
| Notepad | 原生 Document + Edit 统一为 text_area；新建、由测试拥有的 Notepad 通过三轮写值、清空、输入和精确回读 |
| 动作能力 | 不支持的动作在 dispatch 前拒绝；只读 ValuePattern 移除写值与输入；RangeValue 不冒充字符串写值 |
| 展开与选择 | 原生 TreeView 展开/折叠、ComboBox 打开及选择 Second 通过；按 expanded/selected 回读 |
| 窗口列表 | Settings 从四个嵌套 window 节点收敛到一个顶层窗口；完整树保留内部节点 |
| 重排与重建 | structural-v3 使用唯一 Windows HWND；同名按钮重排后 ref 保留，原生控件重建后旧 ref 返回 stale_ref |
| 虚拟列表 | 1,000 行 Win32 owner-data ListView 滚动往返确认；全部 1,000 个行 ref 保持稳定 |
| 决策执行 | 脚本化 provider 选择写值、点击、树展开、下拉展开、横向滚动，五种操作通过真实 Runtime；状态变化后旧决策被拒绝 |

Windows 用 xa11y 提供树和动作，用 comtypes 补充两个原生 UIA patterns。xa11y 会丢弃空 ValuePattern 字符串；实测 RangeValue.SetValue 返回成功但滚动位置仍为 0。补充层使用与 xa11y 一致的 CUIAutomation8/MTA，校验 HWND 的进程、控件类型和 class；必要时在该 HWND 下查找唯一对应的原生文档节点。

原始证据在 [续测目录](evidence/2026-10-02-runtime-followup/README.md)：50 条原生交互记录、五种决策动作、Windows 测试日志和四档基准。Mac 上同一套隔离测试通过，Cocoa 横纵滚动专用 fixture 已成功编译。

### 新基准

每档三次，表中是中位数；不包括 CLI 启动。环境仍为 ARM64 Windows 11 上 x64 CPython 模拟。find 仍重读完整树。

| 内容控件 | snapshot 秒 | find 秒 |
|---:|---:|---:|
| 50 | 0.153 | 0.152 |
| 100 | 0.247 | 0.243 |
| 300 | 0.613 | 0.610 |
| 1,000 | 1.984 | 2.008 |

## P4 接口

- `DecisionProvider.ask(state, questions)` 是可替换的模型接口。
- `JevProvider` 使用 TypeSafe System One API，默认模型 jev-latest；API key 只从调用参数或 TYPESAFE_API_KEY 读取。
- 模型选择由当前原生树生成的 action/ref/value 组合；文字值来自调用者提供的允许列表。
- 默认置信度阈值为 0.7，拒绝未知 choice、非法概率、低置信度及相互矛盾的完成判断。
- 决策携带完整树的摘要。Runtime 在同一次重新读取和元素定位中检查摘要、ref、动作能力；变化后要求重新观察和决策。
- 缺少唯一原生身份的同名同角色重复节点及其后代不会提供给决策层。
- `done` 返回 model_reported；任务完成仍需要自己的可检查成功条件。

接口参考 [computer-use-jev 的 TypeSafe 客户端](https://github.com/paulsmith/computer-use-jev/blob/main/typesafe/client.go)。隔离测试和脚本化 native dispatch 没有调用真实 Jev；它们不代表模型选择准确率。

已有五个保存的原生样本（文本写入、按钮、树、下拉、滚动），可在安全配置 key 后运行：

```bash
uv run python scripts/evaluate_jev.py \
  --cases docs/evidence/2026-10-02-runtime-followup/jev-cases.json \
  --output /tmp/bokkio-jev-evaluation.json
```

该命令只评测保存的快照，并记录动作/ref 命中、延迟和 token。真实桌面下一步可用 `bokkio decide --app … --goal … --allow-value …` 查看决策，增加 `--execute` 执行一个通过检查的动作。

## 待完成与限制

1. **真实 Jev 效果评测已续做**：OpenRouter key 已配置，五个离线样本及五个实时 Windows 任务通过；四类原生难例通过。四档规模的 12 个开发样本中 9 个命中、3 个低置信度拒绝。详见 [P4 报告](P4-REPORT.md)。
2. **macOS 横向滚动实测**：当前前台是 loginwindow，原生 fixture 的读取出现树循环。深度达到 64 层后现在返回明确错误。专用 fixture 已编译，桌面解锁后运行：

   ```bash
   open /tmp/BokkioInteractions.app
   uv run python scripts/verify_macos_horizontal.py --output /tmp/bokkio-macos-scroll.json
   ```

3. **部分可见的虚拟树**：当前 owner-data ListView 的 UIA 暴露全部行；仅暴露可见节点的 provider 尚需原生实测。隔离测试已覆盖节点出现/消失和旧 ref 拒绝。
4. **身份边界**：HWND 标识控件实例，不能保证业务对象身份。UIA 虚拟行、macOS 重排和没有唯一标识的重复节点仍需更多覆盖。Snapshot 检查不能把桌面动作变成事务；检查后 UI 仍可能变化，执行结果需要回读。
5. **P5**：真实 Jev 与跨平台检查点通过后，接入 LLM 子任务规划及原生应用间的执行循环。

## 重跑原生测试

Windows：先构建并启动 disposable fixture，再运行两层验证。

```powershell
dotnet build fixtures\windows-interactions\windows-interactions.csproj -c Release
Start-Process fixtures\windows-interactions\bin\Release\net8.0-windows\bokkio-interactions-fixture.exe
python scripts\verify_windows_interactions.py --output C:\BokkioTasks\runtime-followup
python scripts\verify_decision_runtime.py --output C:\BokkioTasks\decision-runtime.json
```

Cocoa fixture 构建：

```bash
uv run python scripts/build_native_fixture.py \
  --source fixtures/cocoa-interactions/main.swift --name BokkioInteractions \
  --output /tmp/BokkioInteractions.app
```
