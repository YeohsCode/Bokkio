# P5 Windows：部分暴露的原生内容

日期：2026-10-02。继续使用真实 OpenRouter Planner、Jev 和 Windows UIA；测试操作只写入本脚本创建的应用。

## 实现

新增 WinForms [分页 fixture](../fixtures/windows-paged/Program.cs) 与 [实测脚本](../scripts/verify_p5_paged.py)。1,000 个逻辑条目分成 40 页，每页实际创建 25 个按钮。切页销毁旧按钮、创建新按钮；未加载的条目不存在于当前 UIA 树。

这覆盖分页与部分暴露的内容，**不代表真正的 UIA VirtualizedItemPattern 已通过**。任务明确提供 Page 40；本轮也未验证从任意目标编号自主推导页码或搜索路径。

脚本检查初始目标缺失、页面范围、目标激活状态、实际动作顺序，以及跨应用 Notepad 文本。每个目标动作前必须存在包含目标的新原生观察。脚本仅关闭自己启动的进程。

## 实测结果

| 任务 | 结果 | 动作 | 重规划 | 端到端秒数 |
| --- | --- | --- | --- | --- |
| Page 40 → Go → 新出现的 Row 997 → Notepad 写入 | 通过 | 4 | 0 | 50.108 |
| Next → 新出现的 Row 37 | 通过 | 2 | 0 | 38.497 |

第一页只暴露 Row 1–25，第二页只暴露 Row 26–50。换页后 Row 1 的旧引用被拒绝。两条完整模型流程来自同一轮运行，属于开发样本；没有据此估计一般任务成功率。

### 调用耗时

| 调用类别 | 第 40 页与 Notepad | Next 与 Row 37 |
| --- | --- | --- |
| Planner | 38.144 s | 32.969 s |
| Jev，所有调用合计 | 8.167 s | 3.669 s |
| 原生 snapshot | 1.679 s | 0.899 s |
| 原生窗口枚举 | 0.220 s | 0.124 s |
| 原生 perform，含内部验证读取 | 1.089 s | 0.588 s |

计时代理记录真实调用的开始与结束，不改变返回数据。snapshot 包含 Agent 的直接观察及执行前保护读取；perform 内部的读取计入 perform。剩余端到端耗时包含决策处理、trace 序列化与持久化等，**不能单独当作检查点耗时**。检查点细分计时仍待补。

完整原生观察、模型结果、执行和分项计时见 [证据目录](evidence/2026-10-02-p5-paged/README.md)。宿主 111 项隔离回归通过。

## 复现

```powershell
C:\BokkioWorkspace\tools\dotnet\dotnet.exe build fixtures\windows-paged\windows-paged.csproj -c Release
.venv\Scripts\python.exe scripts\verify_p5_paged.py --fixture fixtures\windows-paged\bin\Release\net8.0-windows\bokkio-paged-fixture.exe --output C:\BokkioTasks\p5-paged
```

追加 `--preflight-only` 只检查原生条目暴露与 `stale_ref`，不调用模型。需要已配置的私有 Planner/Jev 才能运行完整两项。

## P5 仍待验收

- 通过原生 UIA 的浏览器兼容性样本。
- 更广的独立应用菜单、文件操作和真正的虚拟化 provider。
- 敏感动作确认策略及检查点细分计时。
- macOS 解锁后的原生滚动与三条跨应用对照。

Windows 阶段验收后接入固定外部任务与官方 evaluator，计划见 [测试集接入](BENCHMARK-PLAN.md)。Recorder 和视觉兜底仍分别属于 P6、P7。
