---
source_path: docs/evidence/2026-10-18-windows-native/README.md
source_version: working-tree-based-on-5579580b96e366a97e14de2f38d3a207ac1fa321
ingested: 2026-10-18
sha256: 20690273d5a4ccd6fd2eb123646d46fc5c7bc01ae84000a90cb0df552d58e8df
---

# Windows 原生整合补验与修复

日期：2026-10-18。基线 `5579580` 加本轮工作树；源码散列见 `sources.json`。这是当前整合功能的开发环境验收；原完整业务矩阵继续暂停。

## 环境与启动

- 本机 VMware Fusion 的独立测试 VM：Windows 11 build 26100，ARM64 系统，x64 Python 3.12.13 经模拟运行；不是 Windows 7–10 或物理 x64 机器验收。
- `vmrun` 电源/列表命令报产品路径错误，但 `vmcli VMX Power Start` 成功。之前仅依据前者判定无法实测，调查不充分；已纠正。VMware Tools 的文件复制和进程执行可用。
- 用户明确允许用保存的测试凭据登录；通过该 VM 已有的本机回环控制台登录，未修改密码、自动登录或锁屏策略。凭据、控制台连接信息、登录截图不入库。
- 基线源码放入独立 guest checkout；使用现有 desktop Python，自带 pywin32 初始化。pytest 及其纯 Python 依赖从已有测试环境复制到独立目录。直接拼接另一个 Python 环境的整个 site-packages 会遗漏 pywin32 的 `.pth` 初始化，这类环境失败不算产品缺陷。

## 真实界面检查

`windows-live-checks.json` / `windows-live-summary.json` 由 `scripts/verify_windows_native_integration.py` 生成；操作仅针对本轮编译启动的 WinForms fixture。

1. 同一进程两个窗口：全量读取访问 2,079 个节点，指定 `Bokkio interactions` 访问 64 个，连续五组均如此，Search / Submit 的 ref 相同。该 fixture 另一窗口含 1,000 个虚拟列表项。
2. 五组交替读取中位耗时：全量 1,672ms，指定窗口 187ms。比较的是**当前版本的不同读取范围**，并非旧版本与新版本同范围对照；不作为一般应用或完整任务提速承诺。VM 上存在测试进程负载，未做隔离性能实验。
3. 8 节点预算明确返回部分观察；通过真实 Core 写入被拒绝，`dispatched=false`。正常完整观察的原生写入经另一次 UIA 读取确认。
4. 启用接管后，真实 `desktop.input` 的标记 SendInput 已发出，文本从独立观察读回，监听器仍 ready。原回执只称 executed，不将 SendInput 回执当成业务验证。
5. 在监听器就绪后，从宿主 VM 控制台发送 Shift 按下/松开。Windows 低级 hook 触发暂停；暂停写入零派发；恢复后旧观察失效，新观察执行成功；原暂停请求使用相同操作 ID 仍返回原拒绝结果。保留原操作状态版本时，已派发检查点返回完成未知。**这是外部模拟输入，不是物理键盘证明，也没有测暂停 P95。**

`edge-windows-summary.json` 由 `scripts/verify_native_web.py` 生成：Edge 独立测试配置、固定本地页、显式 renderer accessibility。327 个原生节点整理为 144 个（仍保留浏览器已暴露的 alert 等上下文）；页面全部 38 个节点逐项保留原 ref 和数据。正文必需事实、六个表格单元格与行/表祖先、表单值、勾选状态、按钮和嵌套页面均通过。这里是只读 backend / 整理器检查；未声称 Windows Core 网页输出截断矩阵或导航/弹窗已验收。Windows Chrome 未安装，未测试。

`macos-resume-check.json` 是真实 Mac CGEventTap 的补验：启用后暂停、监听器确认恢复、300ms 后仍 ready，最后关闭。本轮没有新增 Mac 物理输入试验。

## 修复

- 本机恢复入口先保持暂停，等待监听器排空当前事件队列、检查按住状态并确认；超时取消请求，迟到的确认不能恢复写入。
- Windows UIA 聚焦重新校验原生目标身份和可聚焦状态；启用接管时按需验证原生 action，避免原先拒绝聚焦导致 `desktop.input` 无法执行。后台模式仍不允许该聚焦。
- Windows 启动时补采鼠标按住状态、处理侧键释放；修饰键初态避免通用键别名重复计数，IME 的 VK_PROCESSKEY 不留作按住键。侧键映射有自动检查；启动初态和IME改动仅作代码修正，完整物理/IME矩阵仍待验收。
- 损坏但仍可解析的控制状态 JSON 按不可用处理；空闲心跳写入间隔改为约 200ms，输入、按住状态变化和恢复请求仍立即处理。
- Mac 明示路径采用 POSIX 语义校验；Office fixture 的 file URI 按平台解码。Workflow 测试生成当前平台的应用路径；时间预算测试改用确定性时钟，不再假设 Windows 时钟必然在 1ns 内推进。

导入的文本统一为UTF-8/LF并去除行尾空白；原始字节散列见 `log-import.json`，检查内容和结果保留。

## 回归与失败保留

- 基线真实 Windows：`windows-baseline-tests.txt`，731 通过、35 失败、11 跳过。大量失败由 Mac 固定路径测试产生，未放宽生产应用授权。
- 中间一次异步 Workflow 状态检查出现响应没有 `result`，原测试只报 KeyError，未记录该响应具体错误；当轮775通过、1失败、11跳过。后续增加原响应断言；完整回归通过，独立启动该检查20次均通过。**未重现，根因未定位，不宣称已修复这一偶发问题。** 见 `windows-transient-workflow-failure.json` 和 `windows-tests-and-workflow-repeats.txt`。
- 最终完整回归、跳过原因及退出状态见 `windows-final-tests.txt`、`macos-final-tests.txt` 和 `regression-summary.json`。
- 一次界面脚本错误地假定原始顶层就是 window，实际为 application 包装层；一次把正常 SendInput 的 executed 误期望为 completed；一次等待外部输入过久，旧观察按过期被拒绝。修正测试层次、回执断言及及时输入后在新运行目录通过，没有放宽产品检查。

未完成：Windows Chrome、macOS Edge、Notepad/Explorer/WinUI 扩展矩阵、物理多设备/长输入/IME/锁屏唤醒/监听失效矩阵、两端安装包权限；仍不默认开启接管，不给完整业务速度/费用/成功率结论。

## 复现

在已解锁的 Windows 桌面编译并启动 `fixtures/windows-interactions`；对该进程运行：

```powershell
python scripts/verify_windows_native_integration.py --app FIXTURE_PID --output NEW_EMPTY_DIRECTORY --external-input
```

看到输出目录中的 `awaiting-external-input.json` 后立即从另一个输入来源按下并松开 Shift。若没有外部输入，不传 `--external-input`，结果会明确标记该项未运行。每次使用新目录。浏览器打开 `fixtures/native-web/index.html` 后运行：

```powershell
python scripts/verify_native_web.py --app OWNED_BROWSER_PID --output NEW_EMPTY_DIRECTORY
python -m pytest -q -ra
```

两脚本需要当前源码可导入；依赖按项目安装说明准备。网页检查不启动浏览器，不注入 DOM，不写页面。
