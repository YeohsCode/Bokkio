# 三种实际 Harness 开发验收（2026-10-12）

用户选定当前 Codex、系统 Hermes 和 DeepSeek Harness。测试使用自有 Cocoa Search 字段及可丢弃 CSV，Core 没有增加应用业务规则。基线为 8a94cfa，加本轮 MCP schema 修复；源码指纹和脱敏结果见 [results.json](results.json)。三种指定路径各一份完整样本通过，**调用方覆盖 3/3**，不是每种调用方连续三轮成绩。不同调用路径分别计数，不代表所有 Agent IDE 都已接入或客户生产验收完成。

| 调用方 | 实际路径 | 验证范围 |
|---|---|---|
| 当前 Codex | 本会话 → official MCP stdio client bridge | 直接 MCP 观察/原生字段写入，MCP 代码作业、审批/证据/统计 |
| 系统 Hermes | 现有安装 → MCP stdio；GLM 5.3 Flash | sdk-code 完整闭环 r8 通过；直接 MCP r2 通过，r7 业务核验完成但 CLI exit 1 |
| DeepSeek Harness | Python SDK sdk-minimal + llm-pi-ai + mcp-client；GLM 5.3 Flash | MCP 代码作业 → 委派 Bokkio SDK 原生写入；审批/证据/统计 |

每种调用方要求：capabilities、session.open、desktop.observe/act、code.run、job.get、evidence.check、artifact.read、audit.query、metrics.summary；两种写操作都必须首先挂起审批，并在批准后使用原 ID/参数继续。由测试 runner 外的独立线程管理员只批准精确文字、实际观察的 Search ref 和精确代码/cwd。批准身份来自 OS，审批模式是 **independent_exact_request_automated_fixture_admin**，不是客户人工批准的成绩。

独立判定读取 fixture 自身业务 JSON 和实际 CSV 字节/行内容，不能只采用 Agent 最终回答；另外核对 consumed 审批、完成的作业及工具覆盖。DeepSeek 的 SDK 子请求父操作关联从 request.received 事件独立重算（最初报告误查 execution.intent，计数已更正）。原始 SQLite、stdout、模型 reasoning/session trace、配置和 API key 留在本机私有目录。

## 接入修复与失败轮次

- r1：Hermes 原安装 OpenRouter provider 不读取 inline model.api_key，改为从已有配置在内存中解析并注入 OPENROUTER_API_KEY；原用户配置未改。DeepSeek 插件 retryPolicy 缺少 mode，且解释器 resolve 跟随 venv symlink 到无 Bokkio 的基础 Python。补齐 mode 并保留 venv 入口。
- Codex 桌面捆绑 CLI 0.142.0 不接受当前配置的 gpt-6.1-sol（ChatGPT 登录返回 400）；PATH 中 npm wrapper 另缺可选平台包。没有升级全局安装或换模型。当前 Codex 本会话 bridge 验收单列，**CLI 原生 MCP 接入尚未通过**。
- r2：Hermes 完整原生/代码闭环通过；DeepSeek 旧进程仍加载缺少 mode 的脚本，启动失败。
- r3：DeepSeek 已实际发现并调用 MCP 工具，审批后的模型回合耗时超过 15 秒观察有效期，原生操作零派发拒绝，最终超时。**直接逐回合原生 MCP 路径未通过**，未延长 TTL。
- r4：DeepSeek 的生成代码成功原生写入，验收脚本误断言 completed（实际为 verified），中断 CSV 生成；不是 Runtime 原生动作失败。修正断言后再跑。
- r5：GLM 连续漏传顶层 session_id/cwd 等参数；在仅发生零派发拒绝时停止隔离客户端。runner 还遇到未创建 jobs 表的汇总问题，已处理。MCP schema 原来未声明会话必填，现已对会话工具声明 required session_id，并解释 business arguments 与 envelope 层级；官方 MCP 回归验证缺少 session_id 在派发前报错。
- r6：DeepSeek 代码组合全流程通过，SDK 子请求保持自己的原生审批、观察时效和父子审计，不放宽策略。sdk-minimal 默认 shell/pwsh/DeepSeek adapter 被测试 patch 禁用，仅挂 llm-pi-ai 与 Bokkio MCP；这不是任意代码的 OS 沙箱。
- r7：当前 Codex bridge 完整闭环通过；Hermes 原生复验经历两次零派发过期后完成 native、CSV 和全部证据/统计，但客户端 exit 1，整体仍记失败，未按最终回答覆盖退出状态。
- r8：当前 Hermes 代码组合全流程通过，客户端 exit 0；两项审批 consumed，原生业务/CSV 独立核验正确，6 次 SDK 子请求有父操作关联。最终三种选定调用路径均通过，r2/r7 原生成绩与 r8 组合成绩分别记录。

即便某次模型响应较快，也不能依赖在每个模型回合内完成 15 秒原生观察/审批/派发。当前可用组合路径是 Agent 经 MCP 提交明确批准的 trusted-host 程序，由程序在短事务中观察/执行/读回；模型继续取得作业及证据。程序内原生审批仍由独立管理员处理，本次 fixture 管理员自动批准，人工耗时不属于已验证范围。代码执行不是 sandbox；生产审批与权限部署需要按客户实际条件另验收。

## 复跑

安装本仓库锁定依赖及自有 fixture；Harness 依赖保留在各自环境，Bokkio Core 不新增任何模型依赖。DeepSeek 官方 PyPI 包为 deepseek-harness-sdk==0.1.5rc1 和 deepseek-harness-runtime-bin==0.1.5rc1，SDK 自带 native runtime；无需把系统 Node 加入 Core。

```sh
uv sync --frozen --extra mcp --extra browser --group test
uv run python scripts/build_native_fixture.py --source fixtures/cocoa-runtime/main.swift --output /tmp/BokkioRuntimeContract.app --name BokkioRuntimeContract
uv venv /tmp/bokkio-dsh-sdk
uv pip install --python /tmp/bokkio-dsh-sdk/bin/python deepseek-harness-sdk==0.1.5rc1
uv run python scripts/verify_harness_clients.py --clients deepseek --strategy sdk-code --approve-owned-fixture --dsh-python /tmp/bokkio-dsh-sdk/bin/python --fixture /tmp/BokkioRuntimeContract.app/Contents/MacOS/BokkioRuntimeContract --output /tmp/bokkio-dsh-NEW
uv run python scripts/verify_harness_clients.py --clients hermes --strategy native --approve-owned-fixture --dsh-python /tmp/bokkio-dsh-sdk/bin/python --fixture /tmp/BokkioRuntimeContract.app/Contents/MacOS/BokkioRuntimeContract --output /tmp/bokkio-hermes-NEW
```

脚本默认读取本机现有 Hermes YAML 的特定 GLM 5.3 Flash / OpenRouter 配置，在内存中取得 key；其他部署须修改调用方验收配置，不改 Core。可通过 --hermes、--hermes-python、--hermes-home 指定已有安装。自动审批需显式 --approve-owned-fixture，仅适用于自有可丢弃 fixture。不要把它用于客户应用。

`--clients codex-current` 会启动独立 fixture/管理员并写私有 ready.json；当前 Agent 使用 examples/mcp_call.py，先 capabilities/session.open，再按实际 observe 的 ref 发起原生动作与相同 ID 的批准后恢复，完成代码/证据/统计后写私有 complete.json，runner 才执行独立判定。`--clients codex` 另测桌面 CLI，本机当前模型兼容性失败不能计作通过。

参考实际读取的官方源码：[DeepSeek SDK](https://github.com/deepseek-ai/deepseek-harness/blob/master/python/sdk/README.md)、[MCP client](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.md)、[llm-pi-ai](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/llm/llm-pi-ai/README.md)、[Codex MCP](https://developers.openai.com/codex/mcp)。研究克隆和实际二进制版本分别记录，不用 master 源码版本替代 SDK 包版本。
