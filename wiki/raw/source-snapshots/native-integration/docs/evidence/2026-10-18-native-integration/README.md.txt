---
source_path: docs/evidence/2026-10-18-native-integration/README.md
source_version: working-tree-based-on-262cad6085e8ec1754671f627f048181b1616e5c
ingested: 2026-10-18
sha256: e7e9c4110bf87b11c7359bde4e929807b15f025f40c68a52dab371a0dbf7a077
---

# 2026-10-18 整合证据

结论及支持范围见[实施报告](../../WINDOWS-MACOS-INTEGRATION-RESULTS.md)。本目录区分自动检查、合成provider、macOS开发环境现场和构建，不将它们合并成业务成功率。

| 文件 | 含义 |
|---|---|
| baseline.json / baseline-pytest.txt | 原始源码散列和744通过、6跳过基线 |
| pytest.txt | 整合后完整回归：771通过、6跳过；新增27项 |
| synthetic-*-before/after.json | 相同合成树，两个平台适配器各9次；不是OS调用或真实任务 |
| macos-live.json | 自有Cocoa窗口、独立状态文件读回、输入监听；外部事件为模拟CGEvent |
| macos-live-attempt1.json | 首次AXValue写入失败、效果未知；未自动重发 |
| chrome-macos-live.json | 独立Chrome临时配置的固定页；最终Core接口完整返回9项信息 |
| chrome-macos-core-attempt1.json | 页面标题不等于精确窗口标题，Core正确拒绝；后续脚本使用枚举标题 |
| renderer-checks.json / desktop-control.png | 模拟IPC的渲染器状态操作与界面，不是原生权限验收 |
| desktop-build.txt / desktop-test.txt | TypeScript/Vite与9项Node检查 |
| package-build.txt / packaged-helpers.json | 独立macOS Runtime暂存、导入、辅助程序散列；未安装发布 |
| windows-environment.json | VM启动问题，不能当Windows产品测试 |
| wiki-validation.json | 文档链接、来源、模块和工具映射检查 |
| sources.json | 采集时的工作树源码散列；采集状态字段保留，随本次提交归档 |

合成基准由 `benchmark.py` 生成。旧源码保存在本轮临时目录 `/tmp/bokkio-integration-before`；也可从报告给出的基线提交恢复 `src/` 和 `tests/` 到另一个目录。然后从项目根目录分别运行：

```sh
.venv/bin/python docs/evidence/2026-10-18-native-integration/benchmark.py --source /tmp/bokkio-integration-before/src --tests /tmp/bokkio-integration-before/tests --platform windows --output /tmp/before.json
.venv/bin/python docs/evidence/2026-10-18-native-integration/benchmark.py --source src --tests tests --platform windows --output /tmp/after.json
```

将 `--platform` 改为 `macos` 可复现对应适配器。合成provider没有AX补查，不将它当作Mac全链路耗时。`children_calls`与`read.visited_nodes`是不同计数，均不等于实际系统调用数。

`verify-macos.py`、`verify-chrome-macos.py` 和 `verify-control-ui.cjs` 保留本轮执行脚本；本次文档整理将仓库绝对路径改为从脚本位置计算，探测步骤未改；仍保留临时输出路径。请从仓库根目录运行，并先指定新的临时目录/报告路径，避免覆盖本轮证据。它们会编译并启动自有窗口或独立Chrome实例，结束后关闭测试进程。Chrome测试显式启用了renderer accessibility，没有截图读取或DOM注入。界面截图来自模拟IPC的开发检查，不包含实际账户配置。

无法确认的边界：Windows原生hook/SendInput现场、Edge现场、物理输入/IME/锁屏唤醒、两端安装包权限、真实模型token/费用及业务速度/成功率。普通Python测试通过不补齐这些缺口。
