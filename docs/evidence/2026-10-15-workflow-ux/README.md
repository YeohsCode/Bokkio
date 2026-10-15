# Workflow 真实界面录制与回放验收

此轮修正 Desktop Studio 的实际操作链路。新建 Workflow 只填写名称，录制过程中自动加入实际操作的应用，包括开始录制后才打开的应用。应用绑定仍保存在步骤上，手动拾取只用于编辑具体步骤。

## 最终结果

| 检查 | 结果 |
|---|---:|
| macOS 安装包真实 UX | 20/20 |
| Windows ARM64 安装包真实 UX | 20/20 |
| Python 组件回归 | 720/720 |
| Node 编辑与补录回归 | 5/5 |
| 两端包内源码一致性与无视频检查 | 通过 |

macOS 录制停止 299 ms，Windows 864 ms。Mac 实际回放 16 步，Windows 实际回放 73 步；独立读回均为修改后的 `Bokkio UX edited done`，第二应用分别为 `9` 与 `Courier New`。下一轮从界面暂停、继续、停止后，运行状态为 cancelled，应用结果保持不再变化。

最终测试使用本机现有授权的测试宿主启动安装包；Mac 普通启动的 Bokkio 辅助功能授权仍停在系统账户验证窗口，需要用户在本机完成。

- [Mac 实测结果](macos-installed.json)、[Windows 实测结果](windows-installed.json)。
- [Mac 创建界面](macos-create.png)、[控制条](macos-controls.png)、[编辑后回放](macos-replay.png)、[紧急停止保留草稿](macos-emergency.png)。
- [Windows 创建界面](windows-create.png)、[控制条](windows-controls.png)、[编辑后回放](windows-replay.png)、[紧急停止保留草稿](windows-emergency.png)。
- [Mac 包核对](macos-package-audit.json)、[Windows 包核对](windows-package-audit.json)、[Python 回归](regression.txt)、[Node 回归](node-tests.txt)。

`*-attempt-*.json` 保留本轮失败尝试：输入启动时序、旧 UIA 对象、窗口角色、临时下拉列表、控件真实输入方式、暂停/停止竞态及测试定位器问题。部分旧尝试可能只有已完成检查的计数，必须结合 failure 字段判定；它们均不计入最终通过数。

## 验收入口与执行方式

`desktop/tests/bokkio-desktop-ux.cjs` 从可见界面的「新建 Workflow」开始，操作录制浮条、编辑器、保存、版本库与回放控件。macOS 使用 TextEdit + Calculator；Windows 使用 Notepad + Character Map。

- 应用内交互通过 Playwright 的真实按钮和表单完成。录制开始必须等到浮条窗口实际可见，不能以隐藏窗口的初始 DOM 文字作为就绪信号。
- 外部应用写操作由独立的 OS 输入 actor 完成：macOS CGEvent、Windows SendInput。actor 仅用 AX/UIA 读目标和结果，不使用 Runtime、Client、录制器内部接口或 UIA/AX 的值设置与动作派发。
- 不写入测试 Workflow JSON，不调用内部 API 来开始、暂停、停止、保存、编辑或回放。草稿、版本文件和运行回执只用于独立读回。
- 先确认人工演示的文字/选择确实写入真实应用，再验证录制数据。回放前通过应用界面清空编辑器、重置第二应用，防止把未重置的旧结果当作回放成功。
- 每次使用独立的运行目录和凭证目录；不配置模型或 API Key，固定 Workflow 不调用 Harness Planner 或 Jev。

## 每端检查项

1. 新建无需应用选择。
2. 暂停期间输入不进入流程。
3. 浮条「停止并编辑」完成并显示编辑器。
4. 录制中打开的新应用自动加入。
5. Bokkio 自身控件不被记录。
6. 无未解决捕获错误。
7. 暂停文字不进入保存内容。
8. 停止后继续操作不会追加步骤。
9. 保存步骤完整。
10. 在「内容」页修改录制文字，自动关联的完成检查同步更新。
11. 从版本库重新打开，从界面回放成功。
12. 编辑器独立读回为修改后的预期文字。
13. 第二应用独立读回正确（Calculator = 9；Character Map = Courier New）。
14. 回放浮条暂停成功。
15. 回放浮条继续后可以停止。
16. 停止后应用结果保持不再改变。
17. 主界面「停止并编辑」有效。
18. 主界面「紧急停止」保留捕获步骤。
19. 无 renderer 错误。
20. 整个 UX 场景完成；发生未捕获异常时单独计失败，不能显示部分检查全通过作为验收通过。

## 本轮修复

- 删除 Desktop 的预选应用限制。两端原生捕获器识别新 PID 与实际安装路径，按使用顺序生成应用别名。
- 浮条不再点击穿透或靠近鼠标便消失，提供暂停/继续、停止并编辑、打开主界面；回放时也提供暂停/继续/停止。托盘和 Dock 恢复主界面。
- 捕获输入时的原生目标，避免点击关闭弹窗后再查询丢失目标。Windows 的 mouseDown 在最多 150 ms 的有界交接中取得 UIA 目标，再继续原始鼠标事件；超时仍放行输入。
- Windows 在切换控件和结束录制时补读最后的编辑值；旧 UIA 控件消失不再阻断后续捕获。文本观察等到已排队的按键处理完毕，选择框的箭头选择不会被误记成文字替换。
- Windows 对 dialog 与 window 分别绑定；下拉框打开后的临时列表不会被误当成打开前点击的目标。
- macOS 保留捕获时的原生 AX 角色链，回放按原生角色重新匹配，避免 `AXScrollArea → group` 等规范化差异。输入激活精确的目标文档，不再只检查当前文档。
- 连续回放先清除上一轮浮条和运行绑定，再显示新一轮控件，暂停不会发给旧任务。
- 回放停止优先终止观察重试；会话关闭竞态记为 cancelled，原始未知派发回执仍保持 completion_unknown。
- 手动编辑定位器时清理冲突的捕获信息，修改窗口时重绑窗口上下文；修改录制文字时更新自动关联的完成检查，保留独立人工断言。

## 运行

先构建并安装当前包。Windows 打开一个专用 Notepad 空白文档；macOS 基准自动创建本轮专用临时文本文件。

```sh
BOKKIO_ELECTRON=/absolute/path/to/Bokkio.app/Contents/MacOS/Bokkio \
BOKKIO_TEST_OUTPUT=/tmp/bokkio-ux-run \
npm --prefix desktop run test:ux
```

Windows 使用相同 npm 命令，环境变量指向已安装 `Bokkio.exe`、本机 Python（`BOKKIO_PYTHON`）和独立输出目录。测试将打开/关闭自己的 Character Map 窗口并修改专用 Notepad 文档。

UX 基准、组件回归和完整业务评测分开报告。这里覆盖的是两端真实应用的录制、编辑、保存、回放与停止链路，不将旧组件测试数量计为 UX 成功次数。原完整业务矩阵仍保持此前的暂停状态。
