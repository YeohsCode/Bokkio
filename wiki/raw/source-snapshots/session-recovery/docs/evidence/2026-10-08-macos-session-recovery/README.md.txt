---
source_path: docs/evidence/2026-10-08-macos-session-recovery/README.md
source_version: working-tree
ingested: 2026-10-08
sha256: fe1c67b8dd7e17ba6e05c6eae46133e634d6de4460a610196ddfa2c670a77af8
---

# Mac 交互会话恢复 / Interactive session recovery

日期：2026-10-08，同日早期 blocked 记录之后的复查。

- Finder 桌面可通过 CUA 读取；原生 session_locked=false，AX/capture/events 全部通过。
- Bokkio 自有 Cocoa fixture 三轮各5次原生动作，独立业务检查3/3；另12次滚动通过。fixture进程已关闭。
- Word/Excel/PowerPoint 的新隔离输入均打开；Bokkio 原生树能识别三者的目标文档窗口。初始目标均不达标。
- Planner/Jev 配置构造通过，没有模型调用。Office executor 的构造参数修复，最终校验要求格式目标与执行开始后保存；真实 DesktopAgent 构造路径测试覆盖。
- 主机回归374/374，Office相关19/19；本轮未执行Windows回归。
- 本轮仅恢复/验证与准备，原题Agent任务未开始。早期planned3/started0/blocked3仍作为历史证据保留。
- CUA观察到Word正文AX disabled；PPT空白页区域disabled且New Slide可用。许可证未核验，编辑能力及自动视觉降级仍需实跑。

工作区：`/tmp/bokkio-office-session-recovery-2026-10-08`，准备哈希在打开后再次验证，尚无run.json。

```sh
.venv/bin/python scripts/office_pilot.py run --workspace /tmp/bokkio-office-session-recovery-2026-10-08
```

ready_to_attempt表示此刻允许尝试，不保证任务通过或会话永久可用。运行入口仍会每题重查环境。没有修改密码、自动登录或认证策略。只收录合成fixture与裁剪后的就绪汇总，未归档个人桌面、近期文档或凭据。

English: The Mac interactive session is available again. Native fixture input/select/click passes three rounds, plus twelve scroll actions. Three synthetic Microsoft Office inputs are open and exposed through Bokkio AX. Configuration loads, the executor wiring is repaired, and 374 host tests pass. Benchmark tasks have not started; this is readiness evidence, not a task score. Office editing coverage remains to be checked by execution.
