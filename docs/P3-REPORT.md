# P3：Windows 原生 UIA 验证

> 后续 Windows 滚动、空值、Notepad、窗口筛选与 ref 重排/重建已在 [Runtime 续测](RUNTIME-FOLLOWUP.md) 中补充；本报告保留首次 P3 实测时的结果。

日期：2026-10-02（Asia/Shanghai）

## 结论

同一套 Bokkio API 已在 Windows 虚机内读取真实 UIA 树，并完成三轮原生 WinForms 点击、非空写值、输入、焦点和选择操作。五个应用的统一字段、parent/ref 一致性、ref 唯一性和连续两次读取的 ref 稳定性均通过。失效 ref 返回 `stale_ref`。34 项单元测试在 Windows 通过。

测试重点是原生桌面 Computer Use。Notepad、Explorer 和 Settings 是只读兼容性矩阵；Edge 是附加兼容性样本。动作只作用于固定 WinForms 测试程序。

## 环境与使用

- macOS 上的 VMware Fusion 26H1u1；虚机名 `Bokkio Windows Unattended`。
- Windows 11 IoT Enterprise LTSC 2024 Evaluation，build 26100；4 vCPU、8 GiB RAM、100 GB NVMe、Secure Boot、NAT。该测试配置没有 vTPM。
- 宿主为 ARM64；CPython 3.12.13 为 `win-amd64`，通过 x64 模拟运行 xa11y 0.15.0。
- uv 0.12.21 ARM64、.NET SDK 8.0.425 ARM64；两个 WinForms 程序编译成功，均为零警告、零错误。
- 开发目录：`C:\BokkioWorkspace\Bokkio`。固定工具目录：`C:\BokkioWorkspace\tools`。
- 开发入口：`C:\BokkioWorkspace\Open-Bokkio.cmd`。桌面 Bokkio 快捷方式提供同一入口。
- 本地账户 `Bokkio` 的密码已自动配置并通过 guest authentication 验证，保存在 Mac 的私有目录中；密码不进入仓库。

已修复首次登录的临时用户配置。重启后使用正常的 `C:\Users\Bokkio` 配置，34 项单元测试和五应用 / 三轮原生动作再次通过；开发工具不依赖用户临时目录。一次性自动登录关闭，注册表密码移除。见 [重启证据](evidence/2026-10-02-windows/restart-check.json)。

## 原生应用矩阵

| 应用 / UIA 进程 | 节点数 | 两次 snapshot 总耗时（秒） | ref 稳定 |
|---|---:|---:|---|
| 固定 WinForms fixture | 83 | 0.718 | 是 |
| Notepad / `notepad` | 28 | 0.453 | 是 |
| Explorer / `explorer` | 166 | 1.032 | 是 |
| Settings / `ApplicationFrameHost` | 195 | 0.875 | 是 |
| Edge / `msedge` | 278 | 1.156 | 是 |

表中为重启后的最终矩阵。首次运行的聚合计数也保留在证据目录；应用状态不同会改变节点数。矩阵耗时包含 CLI 启动，不能直接和下方进程内基准比较。Settings 在当前版本由 `ApplicationFrameHost` 承载；窗口枚举确认标题为 Settings，并包含嵌套 window 节点。

## 动作结果

三轮均成功：Submit 点击后 `Status:` 名称改变；Search 写入 `seed` 并确认；清空后输入 `Bokkio Windows run N` 并精确回读；focus 状态确认；Item 1/2 的 selected 状态确认。

点击的 Runtime 返回 `observed`，验收脚本另行确认状态名称改变。清空文本的 Runtime 返回 `unconfirmed`：xa11y 将空 UIA ValuePattern 字符串压缩为 `None`，无法区分空值和没有值。保持这一结果；后续精确输入回读验证了测试流程中的清空效果。没有把 `null` 自动改成空字符串。

## 实测跨平台差异与处理

对照当前 Windows fixture 与 [macOS 原生证据](evidence/2026-10-01-followup/fixture.json)。以下观察限于这些应用与版本。

| 项目 | Windows UIA / macOS AX 实测差异 | 统一处理或限制 |
|---|---|---|
| application 根 | Windows 为 `uia_synthesized=true` 的进程根；macOS 为 AXApplication | 两端输出 application，保留来源字段 |
| 原始角色 | Search 为 UIA ControlType 50004；macOS 为 AXTextField | 统一为 text_field，原始属性进入 platform_data |
| 名称来源 | Windows 为 `uia_name=Search`；macOS 为 AXDescription | 使用统一 name 定位，保留原始来源 |
| 原生标识 | Windows Search 暴露 `hwnd:…`；macOS fixture 未提供稳定 ID | structural-v2 ref 不依赖相同原生标识格式 |
| 被动文本值 | Windows Status 的 name 有内容而 value 为 null；macOS name/value 均有文本 | 状态变化用 name 验证，不假定静态文本总有 value |
| 空文本 | Windows 清空回读 null；macOS 清空回读空串并确认 | Windows 空值保持未确认；非空写入与输入精确验证 |
| 文本点击能力 | Windows Search 只有 set_value/focus；macOS 还暴露 press | 不为 Windows 文本框添加 click |
| 列表结构 | Windows Items 是 list/list_item；macOS Items 是 table/table_row | 各自用实际 role/ref 选择，回读 selected |
| 表格单元格 | Windows cell 暴露 Name Row 0 与 value Alice；macOS cell 本身 name/value 为空 | 保留子树，避免只靠 cell.name 定位 |
| 单选能力 | Windows 原始动作含 select；macOS 原始动作只有 press/focus/toggle | 单选统一使用 click/press 并检查 checked；未在本轮重测 Windows 单选动作 |
| 滚动条 | Windows Horizontal 为 RangeValue，原始动作含 increment/decrement；macOS 数值位置与 AX 滚动条配合 | 当前方向滚动只开放 macOS，Windows 不伪装为相同语义 |
| 窗口结构 | Windows Settings 的 title bar / core window / pane 都可被映射为 window | 窗口筛选保留层次；顶层窗口去重仍需覆盖 |
| 进程识别 | Windows Settings 由 ApplicationFrameHost 承载；macOS System Settings 以应用名出现 | 从 apps 列表与窗口标题确认目标进程 |
| 编辑覆盖 | 当前 Notepad 树包含 web_area，未暴露预期 text_field/text_area | 本轮只验证读取；不能据此声明 Notepad 输入能力 |

两个平台的 provider 动作列表均可能省略 type_text，虽然固定文本框的实际输入方法能运行。后续决策层需要明确区分已验证的方法与 provider 广告的动作。

## 规模基准

原生 WinForms 内容控件数为 50、100、300、1,000。总树节点另含 application、窗口、容器和滚动条。每档预热后测量三次，报告中位数；不包含 CLI 和应用启动。

| 内容控件 | 总树节点 | snapshot（秒） | find（秒） |
|---:|---:|---:|---:|
| 50 | 59 | 0.148 | 0.145 |
| 100 | 109 | 0.236 | 0.233 |
| 300 | 314 | 0.607 | 0.599 |
| 1,000 | 1,014 | 1.965 | 1.964 |

find 当前会重读整个树，因此耗时与 snapshot 接近。这是 ARM64 Windows 上 x64 Python 模拟的结果，不代表原生 x64 主机，也不是 xa11y 原始单次批量 snapshot 的性能。原始时间见 [benchmark.json](evidence/2026-10-02-windows/benchmark.json)。

## 后续事项

- Windows 方向滚动、Notepad 文本控制和更多 app-specific UIA patterns。
- 虚拟化、结构重排和嵌套窗口筛选；当前 ref 不保证跨节点重建的业务身份。
- 优化重复遍历与 find 的整树读取，再评估是否需要迁移 backend。
- P4：Jev 局部元素和动作选择；后续再接 LLM 规划。

本轮无需绕开 xa11y；保留上述能力限制。证据索引见 [Windows evidence](evidence/2026-10-02-windows/README.md)。
