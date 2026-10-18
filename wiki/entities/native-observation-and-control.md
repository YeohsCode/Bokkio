---
title: "原生读取、网页整理与用户接管"
created: "2026-10-18"
updated: "2026-10-18"
type: "entity"
tags: ["runtime", "native", "windows", "macos", "recovery", "evidence"]
sources: ["src/bokkio/observation.py", "src/bokkio/web_view.py", "src/bokkio/desktop_control.py", "src/bokkio/input_monitor.py", "src/bokkio/runtime.py", "src/bokkio/desktop_decision.py", "src/bokkio/runtime_workflow.py", "docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md"]
confidence: "high"
---

# 原生读取、网页整理与用户接管

三项功能已接入当前0.3.0工作树，完整双平台支持范围验收未完成。“本轮实现”不代表另有一份未公布的新功能安排；下一步先补现场与安装包验收。^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L5]

## 已实现接口

| 入口 | 行为与限制 |
|---|---|
| desktop.observe | Windows在递归文档正文前选择窗口；两端支持read_nodes/read_timeout/read_depth |
| read.complete=false | 部分观察；total_nodes=null，清除动作，Core不能用它批准写入 |
| view=web | 在已授权Chrome/Edge窗口中整理原生web_area及弹窗/祖先路径，保留ref和表格层次 |
| desktop.control | 只读接管状态；不接受启用、关闭或恢复参数 |
| 本机UI / bokkio control | 用户开启、关闭或明确继续；默认关闭接管 |

max_nodes/max_bytes仍限制输出，读取预算在遍历和补查边界协作检查。直接子节点整批枚举、已开始的阻塞调用不能被这些值硬中断。Mac主遍历和AX补查共享预算。^[src/bokkio/observation.py#L13] ^[src/bokkio/runtime.py#L330]

网页整理不截图、不注入DOM，不会读到浏览器未暴露的信息。区域缺失或无法确定时明确失败；同时检查read.complete与truncated。无法证明属于目标窗口的额外菜单/弹窗只提供只读上下文。^[src/bokkio/web_view.py#L6] ^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L25]

## 接管与恢复

独立监听器使用Windows低级hook或Mac只读CGEventTap，只提交事件类别、时间和暂存的按住状态。SQLite共用暂停状态；原生辅助程序检查短时状态文件。自身输入有统一标记，未知来源也按干扰处理。^[src/bokkio/input_monitor.py#L15] ^[src/bokkio/desktop_control.py#L29]

用户操作后停止后续桌面写入；明确继续会更新状态版本。旧观察、旧排队许可与旧Jev决策失效，需重新读取。监听异常/心跳过期时，已启用接管的任务拒绝新写入。^[src/bokkio/desktop_control.py#L107] ^[src/bokkio/runtime.py#L388] ^[src/bokkio/desktop_decision.py#L149]

Workflow保留已完成步骤和原回执，从原运行记录继续。确认零派发的暂停请求可在新观察后提交新请求；结果未知不能清零或重发。UI的继续按钮恢复输入许可，没有宣称冻结或自动恢复整个SDK线程。^[src/bokkio/runtime_workflow.py#L277] ^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L33]

已开始的系统调用和排队输入不可撤回，检查与交给OS之间仍有时间间隙；按住同一物理键、IME、睡眠唤醒和多RDP会话尚未验收。任意宿主脚本可以绕开Core，不能将该功能当成宿主代码隔离。^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L94]

## 当前证据与下一步

- Python771通过、6跳过；Node9通过；TypeScript/Vite和Mac独立Runtime暂存通过。
- Mac自有窗口、独立状态文件读回和模拟输入接管已有现场结果；Chrome固定页经真实Core保留9/9必需信息。
- Windows测试VM未启动；两端Edge、物理键鼠/IME/锁屏唤醒和安装包权限仍待完成。合成Windows多窗口遍历减少不能外推为完整任务提速；Mac同例没有减少遍历。

依据：^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L39] ^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L71]

下一步按实施报告顺序补Windows/浏览器现场、物理输入与恢复、两端安装包验收，修复发现的问题。完整任务耗时/费用/成功率评估须遵守原业务矩阵的暂停要求。底层分页、阻塞调用隔离、多RDP会话隔离只有出现瓶颈/需求后才另行评估，当前未安排开发。^[docs/WINDOWS-MACOS-INTEGRATION-RESULTS.md#L106]

关联：[[entities/native-runtime]]、[[entities/runtime-core]]、[[summaries/current-status]]、[[summaries/pending-and-known-gaps]]、[[concepts/action-verification]]。
