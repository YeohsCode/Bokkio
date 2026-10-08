# P7.1 原生窗口截图 / Native window capture

更新：2026-10-08。**P7 已进入实现；P7.1 截图接口、自绘应用及验收脚本已落地，交互桌面的像素验收尚未通过。**

## 实现

- `bokkio capture --pid PID [--hwnd HWND] --output new.png`：Windows 内执行，保存客户区 PNG 和 `new.png.json`；不依赖 AX/UIA 树读取。
- 每份结果包含 PID、HWND、进程创建 FILETIME、窗口类、窗口范围、客户区屏幕原点、物理像素尺寸、窗口 DPI、采集时间、耗时及图像 SHA-256。
- 坐标以客户区物理像素表示；映射到屏幕时加原点，不再乘一次 DPI。窗口的逻辑单位比例单独记录。
- `PrintWindow(PW_CLIENTONLY)` 在独立子进程执行，默认五秒超时；临时设置线程 PerMonitorV2 DPI 上下文并恢复。没有桌面全屏捕获，也没有点击或输入派发。
- 只接受明确 PID 范围；多窗口必须指定 HWND。窗口消失、PID 不符、隐藏、最小化、几何/DPI 变化、权限拒绝、受保护窗口、非交互桌面及工作进程超时均有结构化错误。
- PNG 只表示采集完成，`content_verified=false`；调用成功不能证明画面内容正确。图像和元数据输出拒绝覆盖已有文件。

图像绑定窗口身份并不自动授权后续坐标动作。截图时效、窗口重验、OCR/候选定位、输入预算与动作后验证属于 P7.2–P7.4，尚未实现。

## 自绘测试应用与验收

`fixtures/windows-visual` 使用一个 WinForms 客户区绘制业务按钮与输入区域，没有内部 Button/TextBox 控件。四角固定色块可独立检测裁剪偏移、通道顺序、空白画面与上下翻转。只读验收工具 `scripts/verify_p7_capture.py` 计划执行：

1. 三次独立启动、捕获、PNG CRC/像素检查、DPI/坐标与 fixture 状态对照。
2. 移动每个自有窗口，再捕获；原点应变化，像素应保持。
3. 核验内部业务标签未通过 Accessibility 暴露。
4. 错误 PID、已关闭窗口、最小化、多窗口歧义、捕获保护和阻塞 WM_PRINT 超时六类故障。

这些交互用例目前**未执行成功，不计作 0/3 失败或 3/3 通过**。实际多显示器/多 DPI、遮挡、GPU/自绘第三方应用和更广泛故障仍需扩展。

## 已验证的结果

| 项目 | 结果 |
|---|---|
| 主机隔离回归 | 314/314；包含 21 项截图相关用例 |
| Windows 隔离回归 | 最终 314/314 无警告；首次运行一项 pytest 缓存目录写入警告，改用专用测试缓存目录后复测通过 |
| Windows 自绘应用构建 | .NET 8 ARM64 构建成功，0 编译错误/警告 |
| Windows 实际捕获前置检查 | 自有 fixture 已就绪，guest runner 捕获返回 `desktop_unavailable`，没有产出图像 |
| Mac UI 检查 | CUA 返回 Mac 锁定且自动解锁失败，无法接管虚机登录界面 |

本轮 VMware guest authentication、文件传输、构建和回归可用。通过 guest operations 创建的进程没有可用交互输入桌面，实际截图前置检查明确拒绝；因此暂不能完成图像与坐标的实机验收。需要已有 Windows 测试用户的交互桌面可用。没有修改登录策略、自动登录或安全设置。证据见 [索引](evidence/2026-10-08-p7-capture/README.md)。

```powershell
# 在已登录的 Windows 测试用户会话中执行
.venv\Scripts\python.exe scripts\verify_p7_capture.py `
  --fixture C:\BokkioWorkspace\P7Visual\bokkio-visual-fixture.exe `
  --output C:\BokkioTasks\p7-capture-v1
```

验收通过后，顺序推进 OCR/视觉候选和有界坐标动作；Mac Office 的 Bokkio 适配仍是独立待办。

## Mac 独立路径复查（同日）

CUA 无法接管桌面不等于全部 Mac 测试不可执行。独立 ScreenCaptureKit 诊断已完成三次自有窗口截图 3/3，当前 AX 仍返回 application 代理。此前 Mac 受阻结论仅适用于相应交互路径；窗口截图与视觉准备可以继续。此诊断尚未集成到 Bokkio Runtime，详见 [Mac 复查](MACOS-CAPTURE-PROBE.md)。

## API 依据

微软文档说明 [PrintWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-printwindow) 是同步调用，客户区模式使用 PW_CLIENTONLY；[线程 DPI 上下文](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext) 返回旧值供恢复。[CreateDIBSection](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection) 的像素读取前需要 GDI 同步。[GetWindowDisplayAffinity](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowdisplayaffinity) 并非所有窗口都支持，因此元数据区分 known/unavailable，显式保护或权限拒绝会停止捕获。没有将该查询声明为通用内容保护保证。

## English

P7 implementation has started. P7.1 provides scoped Win32 client-area PNG capture, an explicit physical-pixel coordinate mapping, a custom-drawn fixture and an independent acceptance runner. Capture records PID/HWND, process creation time, class, geometry, DPI, time and image hash. PrintWindow runs in an isolated process with a bounded timeout. Ambiguous scope and native faults are structured; existing output files are preserved. Capture does not dispatch input or prove visual content correctness.

Host and Windows each pass 314 isolated tests, including 21 capture tests. The fixture builds without compiler errors or warnings. The first Windows test run has one cache-write warning; the final run uses an owned test cache directory and passes without warnings. A real owned-fixture preflight returns `desktop_unavailable` and produces no image. CUA also reports that the Mac is locked. Guest operations support builds and tests but currently provide no interactive input desktop for capture. No login/security policy was changed.

The three native pixel/geometry runs and six window-fault cases remain unstarted; they are not counted as successful acceptance. Run the supplied verifier in the logged-in Windows test session, then proceed to P7.2 visual candidates and P7.3 bounded input. Multi-monitor/DPI, GPU applications and wider reliability coverage remain separate work. Mac Office CUA results do not substitute for Bokkio integration.
