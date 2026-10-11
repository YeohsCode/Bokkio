# P7：Mac 与公共视觉接口 / Mac and shared visual interface

更新：2026-10-11。**公共 OCR、Mac provider、Agent/Jev 和 CLI 已实现；主机 519/519。固定子任务实机输入在三个新进程通过 3/3，各两次尝试。完整 Office 开发轮 r28、r30 各通过 3/3；最新完成轮 r33 为 0/3，连续三轮 3/3 尚未达到。按用户要求提交当前快照，实机验收暂停。** Windows 开发暂缓。

## 公共接口

`src/bokkio/visual_runtime.py`提供：

- `WindowScope`：明确platform/PID/title及可选window_id。每个PID绑定一个固定标题窗口。
- `VisualObservation`：截图字节、OCR、窗口与进程创建身份。字节只在本机执行器内流转，不进入trace。
- `VisualPolicy`：默认每app最多12次OCR观察（包括输入后的验证）、64个候选、置信度至少0.8；输入标签需显式声明。
- `VisualProvider`：capture / prepare_input / execute协议；Windows后续可实现相同协议，本轮没有Windows OCR或输入实现。
- `MacVisionProvider`：复用ScreenCaptureKit、Apple Vision和现有有界输入helper，不新增模型依赖。
- `HybridBackend`：封装现有原生backend，提供planner观察、step准备和动作执行hook。

公共OCR文字/边界/置信度验证允许Mac/Windows规范化数据；Windows测试仅为模拟协议数据，不代表真实Windows支持。

## Agent接入

1. 原生观察具有与意图匹配的可执行目标时继续原生路径，无OCR调用。
2. 无目标/能力时，在显式授权窗口生成`visual_text`候选。无效AX树或AX权限不足可独立只读采集，输入仍受Mac会话/权限/前台守卫约束。
3. Planner看到文字、来源、置信度及广告动作；Jev只选择候选token。OCR文字不推断为按钮或可写原生控件。窗口外的原生树不会进入这个观察。
4. `visual_click`点击唯一文字；`visual_type`只作用于声明输入标签，文字来自allowed_values。有重复标签、已知禁用/只读/原生能力或歧义的同名目标时不通过OCR绕过。
5. 捕获哈希、窗口/进程身份、几何、时效、前台与事件权限由既有helper复查；派发后重新观察并核对整个subtask success。
6. 已经为真的静态条件不能证明一次视觉命令；错误原生success角色在输入前要求重规划为真实OCR角色。外部/破坏性风险和敏感文字目标拒绝。
7. 未知完成不换路径重试，仅只读核对一次；成功条件由假变真才继续，静态已真条件不能证明命令。无法确认时停止。明确零派发的过期/变化截图可在现有 Agent 预算内重新观察。

视觉观察缓存只在有效截图合约内复用。恢复时窗口、输入标签与策略必须保持相同，已使用的OCR预算随trace保存。关闭进程/窗口和标题变化需要重新授权/绑定；本版不自动扩大范围。

## 使用

将例子中的123替换为真实fixture PID；输入标签是调用者提供的字段声明。

```sh
uv run bokkio run --allow-app 123 \
  --visual-window '123=BokkioVisual' \
  --visual-input-label '123=Enter code' \
  --max-visual-captures 12 \
  --goal 'Click Run check, verify Checked appears, then type ABCD into Enter code and verify ABCD appears.' \
  --trace /tmp/bokkio-visual-run.json
```

默认 run 保持原生路径。视觉开关绑定数字 PID 和精确标题，不能使用模糊应用别名。Office 专用 wrapper 保留原生菜单/弹窗，只为 PPT 声明标题输入；原生 combo 的捕获边界输入另有字段身份/焦点核对。通用跨窗口、标题变化、无标签输入、图标检测、复杂键盘组合及视觉 Workflow 重放仍待扩展。

Python调用示例：

```python
from bokkio.visual_runtime import HybridBackend, MacVisionProvider, VisualPolicy, WindowScope
from bokkio.xa11y_backend import Xa11yBackend

backend = HybridBackend(
    Xa11yBackend(), MacVisionProvider(),
    {"123": WindowScope("macos", 123, "BokkioVisual")},
    policies={"123": VisualPolicy(input_labels=("Enter code",))},
)
# 将backend传给现有DesktopAgent；Planner/Jev继续接收文字和闭合选项。
```

## 验证结果

- 主机回归 519/519，涵盖原生零 OCR、模拟 click/type、混合路径、角色修复、范围/歧义、取消/预算、未知完成只读核对和恢复约束；最新 Swift helper 编译通过。
- 三个新自绘 Mac 进程：固定 Planner 两步合约、真实 Jev/Agent 输入、独立业务 JSON 3/3；每次恰好一次点击和 CODE1/2/3。原始版尝试 3/4/4；当前版各两次尝试。它不代表通用 Planner 验收，计数 OCR 高置信筛选仍有限制。
- 完整 Office 开发轮 r28、r30 各通过 3/3；最新完成轮 r33 为 0/3，连续三轮 3/3 尚未达到。按用户要求提交当前快照，实机验收暂停。 Word/PPT 独立 GUI 探针全部文件检查通过，分别报告，不计入完整 Agent 成绩。
- Mac 已解锁，断电后输入 r9 为 3/3，各两次尝试；固定合约测试不替代完整 Office 验收。
- 当前 wheel 构建通过，29 个打包源码成员与当前源码一致，摘要见验证记录。OCR 本地执行，截图不上传业务模型；现有 Jev/Planner 文字调用仍计费，没有 Astra 依赖。

命令：

```sh
uv run python scripts/verify_macos_visual_bridge.py \
  --fixture /path/to/BokkioVisual.app --output /tmp/new-bridge-evidence --model
```

这条命令只读截图/决策。真实输入命令使用 `scripts/verify_macos_visual_input.py`，相同 fixture/output 参数，启动三个新进程并独立读取业务状态。详见[本次证据](evidence/2026-10-10-office-progress/README.md)和[此前只读证据](evidence/2026-10-09-visual-bridge/README.md)。

## English

Shared WindowScope/VisualObservation/VisualPolicy/VisualProvider interfaces and MacVisionProvider are implemented. HybridBackend routes missing native targets to scoped OCR candidates with declared input labels, closed Jev choices and post-action conditions. Resume preserves scope/policy/provider settings and observation budgets. Unknown completion never reposts input: a read-only check may continue only when success changed from false to true.

The optional run CLI binds exact PID=TITLE windows and declared PID=TEXT input labels. OCR remains local, while existing text-model calls are still billed. Windows providers, visual Workflow replay, icons, unlabeled fields and changing-window/dialog flows remain pending.

Host regression passes 519 tests. The current helper passed real click/type 3/3 in fresh processes with fixed Planner contracts and independent business checks. Full Office development rounds r28 and r30 each passed 3/3. The latest completed round r33 passed 0/3; three consecutive 3/3 rounds remain pending. Live acceptance is paused for the requested code snapshot. Wheel build passed; all 29 packaged source members match the recorded current source. See [latest evidence](evidence/2026-10-10-office-progress/README.md).
