---
source_path: docs/evidence/2026-10-09-visual-bridge/README.md
source_version: working-tree
ingested: 2026-10-09
sha256: ceb87760da97b66ab25bc37442275e7859535844a10955d629a76d8f49594c33
---

# Mac 公共视觉接入证据 / Mac visual bridge evidence

日期：2026-10-09。主机 **435/435**，新增公共视觉模块测试 **24项**。最新三次独立自绘Mac窗口的截图、Apple Vision OCR、公共候选及HybridBackend观察通过 **3/3**；真实Jev三次均选择visual_click、置信度1.0（阈值0.7）。这些调用只有文字候选，没有传输原始截图。

## 分开报告

- [round-1.json](round-1.json)：0/3；无效AX树阻断Hybrid观察，且测试把未识别的计数文字列为必需目标，历史失败保留。
- [round-2.json](round-2.json)：修复授权窗口独立观察，改为检验Run check/Enter code/Ready；3/3只读通过。计数文字未达到当前候选条件，未声称计数OCR通过。
- [round-3.json](round-3.json)、[round-4.json](round-4.json)：新fixture布局和最新公共接口，均3/3只读通过；计数文字仍未被高置信度候选保留。
- 最新[validation.json](validation.json)：435项回归、wheel源码校验、实机与模拟证据边界。
- 模拟Agent完成视觉点击、声明输入与独立业务状态检查；原生可用时零OCR、缺失原生目标后的重规划、取消/预算/跨窗口/未知完成/恢复约束均有测试。模拟执行不计作GUI成功。
- Mac仍报告锁屏，真实activation helper拒绝输入准备，fixture业务计数与输入均保持初始值。没有鼠标/键盘派发，真实输入与Office原题分数未新增。

各轮代码和fixture版本有变化；源码哈希保留在报告中。最新三次模型调用的usage/cost为provider返回值，只覆盖这些决策，不包含其他轮次或Planner费用。无Windows实测、无官方benchmark分数。截图和完整原生树没有发布。

接口与使用见[实现报告](../../P7-VISUAL-BRIDGE.md)。本目录的SHA256SUMS覆盖除清单自身外所有文件。

## English

Host regression passes 435 tests, including 24 public visual-runtime cases. Latest native read-only acceptance passes 3/3 independent Mac fixture processes; real Jev selects visual_click at confidence 1.0 in all three. Raw screenshots are not sent to the decision provider. The simulated Agent click/type loop is verified separately.

Round 1 failures are retained. Counter-text OCR remains unaccepted; the read-only target checks cover Run check, Enter code and Ready. The locked-session activation guard rejects input preparation, with unchanged independent fixture business state. No live input or new Office score is claimed. Windows was not tested. Source versions and provider-reported usage remain in the reports.
