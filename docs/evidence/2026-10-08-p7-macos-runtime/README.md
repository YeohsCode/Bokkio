# P7 Mac Runtime evidence

2026-10-08。当前 Mac，自有 NSView 绘制窗口，ScreenCaptureKit + Apple Vision；没有浏览器/DOM、模型调用或成功输入派发。

- `runtime-v1/`、`runtime-v2/`、`runtime-v3/`：三轮代码版本分别归档。最终 v3 正常流程 3/3、拒绝 8/8；每轮有 fixture 独立几何状态、PNG、OCR/身份元数据和目标候选。
- `input-initial.json` / `input-final.json`：均为输入会话前置拒绝，`dispatched=0`，不计作点击/输入成功。
- `cli.json` 与 `cli-capture.*`：实际 `capture --ocr` / `visual-find` 返回 0。
- `initial-ocr.*`：首个自绘应用 Runtime/OCR 检查，保留其历史元数据。
- `host-tests.log` / `windows-tests.log`：最终两端各 355/355。
- `source-hashes.json` / `guest-source-hashes.json`：最终 v3 Runtime/验证器源码匹配本地代码；五个 guest 核心文件哈希一致。
- `checksums.json`：归档文件字节哈希。

输入尚未正向验收，自动 Planner/Jev/Workflow 降级未接入。多比例/显示器、真实办公布局及更多故障待扩展。原始图像只含自有合成界面，API key、账户、无关窗口及详细扫描报告不在归档中。详见 [报告](../../P7-MACOS-VISUAL.md)。

## English

Final native capture/OCR/candidate tests pass 3/3 independent runs and 8/8 rejection cases. Initial code versions remain separate. Explicit region/window-ID selection and real CLI capture/find calls pass. Host and Windows each pass 355 tests; final source/guest hashes match. Input preflight rejects with zero dispatch; positive input and automatic Agent/Workflow fallback are pending. All screenshots are owned synthetic fixtures; no credential, account or unrelated window is archived.
