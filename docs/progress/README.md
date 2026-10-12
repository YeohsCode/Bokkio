# 跨环境 Agent 共享进度

此目录通过 Git 同步，是 macOS、Windows 和其他开发环境接续项目的公共入口。最新主线是通用 Computer Use Runtime。先读本页和状态，再选取待办；旧 Office/Planner 路线只作为历史回归。

| 文件 | 用途 |
|---|---|
| [实施计划](../PLAN-REPOSITIONING.md) | 产品定位、三天目标、契约和原始验收门槛，保留指定路径 |
| [测试加强计划](../TEST-STRENGTHENING-PLAN.md) | 12题业务保留集、三调用方、分轨评分、审批/故障与执行顺序；首轮已执行，复测推进中 |
| [测试工作包](test-strengthening.json) | EVAL-01～08 的依赖、验收条件与计划分母，首轮与复测 46 个结果／26 个启动；原始与更正评分单列，完整矩阵未完成 |
| [当前状态与完成度](STATUS.md) | 已完成范围、证据、待验收、暂缓事项 |
| [结构化状态](state.json) | Agent 可读取的平台状态、能力分母及待办 ID |
| [接续说明与待办](HANDOFF.md) | 两端启动、验证、证据保存及协作规则 |
| [详细交付报告](../RUNTIME-DELIVERY.md) | 实现和实测的具体边界 |
| [Runtime 使用指南](../RUNTIME-GUIDE.md) | 配置、调用和信任边界 |
| [验收证据](../evidence/2026-10-12-runtime-macos/README.md) | 脱敏摘要、历史失败和校验和 |
| [三种 Harness 验收](../evidence/2026-10-12-harness/README.md) | 当前 Codex、系统 Hermes、DeepSeek Harness 的实际路径、版本与失败记录 |

进度、计划、待办、验收摘要必须提交 Git，不放入 gitignore。每次完成一个待办，更新 STATUS.md 和 state.json，补充对应证据，并在提交说明中写清平台与验证结果。不要把旧平台成绩算作新 Runtime 验收。

原始运行数据库、截图、凭据、客户数据和运行中的 stdout 保留在各环境的私有目录；这里只存可共享的证据摘要。另一端先 git pull，再使用当前源码和 uv.lock 安装，不依赖这台 Mac 的 dist 或临时目录。

[自主业务测试报告](../evidence/2026-10-12-business-eval/README.md)：保留首轮失败与评分器缺陷，新增轮次单列。
