# 发布前隐私与密钥检查 / Pre-publication privacy review

日期：2026-10-04。范围为原有 18 个 Git 提交、当前发布文件，以及解压后的原生测试证据。检查工具：Gitleaks 8.30.1 与额外的历史 blob / gzip 文本检查。扫描报告保存在本机临时目录，不包含在发布仓库。

## 结果

- 历史提交扫描及发布候选扫描未检出实际 API key、GitHub token 或私钥。额外检查覆盖压缩轨迹中的 key 前缀、Bearer 值、邮件地址、个人主目录和局域网地址。
- `docs/P3-READINESS.md` 包含个人虚机绝对路径，已改为 `/path/to/Windows11.vmwarevm`。
- 固定上游 WAA 配置中的 `/Users/Docker/...` 是通用 benchmark 路径，保留原始数据及校验哈希。
- API 配置和虚机认证材料保存在仓库外；忽略规则排除 `.env`、虚拟环境及临时缓存。发布树没有包含这些配置。
- 提交作者使用用户指定的 `andreas.dev@outlook.com`。发布历史整理为一个无父提交的 `init commit`；旧历史引用和本地 reflog 清理后，回收不再引用的 Git 对象。

测试证据保留全部失败、中断、源码哈希、独立校验和产物；压缩证据也接受密钥与隐私检查。这里的“未检出”是本次扫描结果，不保证所有类型的隐私数据都能被自动识别。

## English

The review covers the original 18 commits, publication files, and decompressed native-test evidence. Gitleaks 8.30.1 and additional history/blob checks found no actual API keys, GitHub tokens or private keys. Checks also cover credential prefixes, Bearer values, emails, personal home paths and private network addresses.

A personal VM path in `docs/P3-READINESS.md` was replaced with `/path/to/Windows11.vmwarevm`. Generic Docker paths in the pinned upstream WAA fixture remain unchanged to preserve source hashes. API configuration and VM credentials stay outside the publication tree; ignored environments and caches are excluded.

The requested author email is used. The published history contains one parentless `init commit`; prior local history references and reflogs are removed and unreachable objects are pruned. Failures and benchmark provenance remain in the evidence files. These are scan findings, not a guarantee that every form of private information is detectable.

## 2026-10-04 pilot 证据检查（历史状态）

新增固定五题 pilot 的证据逐份解压后检查。最终 Gitleaks 扫描覆盖证据及本轮源码、脚本、测试和固定输入，共约 190 MB 文本，报出 151 项 generic-api-key；逐条核对均为 `uuid4().hex` 生成的 32 位派发请求标识，没有实际凭证。附加检查覆盖 559 个证据文件：guest 测试日志中的临时用户目录已规范化为 `C:/BokkioTestTemp`；原始 benchmark 的通用 Docker 路径保留。复查未检出其他个人主目录、私人邮件、局域网地址、API key 前缀、Bearer 凭证或私钥。558 个归档文件哈希、18 项产物字节及哈希校验通过，v13 执行的七个源码哈希与该轮代码一致。扫描报告留在仓库外。

The final Gitleaks scan covered about 190 MB of decompressed evidence, source, scripts, tests and pinned inputs. All 151 generic-api-key matches were verified as random 32-character dispatch UUIDs. Additional checks covered 559 evidence files. A guest test log's temporary user directory was normalized to `C:/BokkioTestTemp`; generic Docker paths in original benchmark inputs remain unchanged. Rechecks found no other personal home paths, private emails, private network addresses or credential material. All 558 archive hashes and 18 artifact byte/hash records passed verification. The seven source hashes executed in v13 matched that round's code. Scan reports remain outside the repository.


## 2026-10-05 P5/P6 首版候选续检（历史状态）

- 对当前仓库候选逐份解压检查，共 2,081 个文本文件、830,637,743 字节（约 831 MB）。Gitleaks 报出 257 项 generic-api-key；按文件与行号逐条核对，全部为 `"token": "<32 hex>"` 的随机派发 UUID，未发现实际凭证。
- 补充检查对全部证据覆盖个人主目录、邮件地址、局域网地址、API key 前缀、Bearer 值和私钥，未检出。测试临时目录统一为 `C:/BokkioTestTemp`；原始 Docker 基准路径保持。应用发现失败信息中的无关应用 inventory 已摘除，保留错误原因、动作数及分母；仓库外原始诊断未发布。
- P5 的 1,051 个归档文件哈希及 34 项产物长度/SHA-256 通过；P6 的 62 个归档文件哈希、12 个 Workflow 内容哈希与原始 trace 输入字节通过。v26/v27 七个 P5 源码哈希一致并匹配当时的代码；v4 六个 P6 源码哈希匹配当时的首版实现。
- macOS 主机和 Windows 虚机各 265 项隔离测试通过；原生结果和所有失败轮次分别保存。当前续检针对本地候选，扫描报告保存在仓库外。

The final local P5/P6 candidate scan covered 2,081 text files and 830,637,743 decompressed bytes. All 257 Gitleaks matches were checked against their source lines and classified as random dispatch UUIDs. Additional evidence checks found no personal home paths, email addresses, private network addresses or credential material. Unrelated discovery inventory was removed from error strings while causes and denominators remain intact. All 1,051 P5 archive hashes, 34 artifact byte/hash records, 62 P6 archive hashes, 12 workflow content hashes and original input-trace bytes passed verification. Executed P5 and P6 source hashes match that historical candidate implementation. Both platforms passed 265 regression tests then. Scan reports remain outside the repository.

## 2026-10-05 P6 闭合续检

- 扫描时覆盖 2,181 个源码/文档/解压证据文本文件、872,185,041 字节（约 872 MB）。Gitleaks 报出 257 项 generic-api-key；按原文件行逐一核对，全部为随机 32 位派发 UUID，未发现实际凭证。附加证据模式检查未检出个人主目录、邮件、局域网地址、密钥前缀、Bearer 值或私钥。
- 新闭合归档的 91 个字节哈希、11 个 Workflow 内容哈希、19 个检查点内容哈希、14 份文本产物的预期字节/长度/SHA-256 均通过。closure v3 和 core v5 的八个共用源码模块匹配当前实现，各 verifier 哈希单独核验。P5 历史评分继续绑定其原源码版本。
- 最终主机与 Windows 各 292 项隔离回归通过；原生失败轮次和未开始分母保留。API key、虚机认证、扫描器详细报告与私有配置继续保存在仓库外。当前检查针对未提交的本地候选。

The P6 closure scan covered 2,181 text files and 872,185,041 decompressed bytes at scan time. All 257 Gitleaks matches were verified as random dispatch UUIDs. Additional evidence-pattern checks found no personal paths, emails, private-network addresses or credential material. All 91 new archive hashes, 11 workflow hashes, 19 checkpoint hashes and 14 expected artifact byte/hash records passed. Final native closure/core source hashes match the 2026-10-05 implementation. Host and Windows each pass 292 tests. Failed and unstarted attempts remain visible; keys, VM authentication and detailed scanner reports stay outside this uncommitted local candidate.

## 2026-10-06 Mac evidence

52 new compressed archives were checked for personal home paths, emails, credential prefixes, Bearer tokens and private-key material; no findings. Eight Workflow hashes and 21 checkpoint hashes passed validation. Final Mac P6 source hashes match this candidate, including the table_row capability fix. Host tests pass 293/293; the prior Windows result remains 292/292. Earlier Mac failures and incomplete receipt coverage remain disclosed. No key/config or unrelated application inventory was added. This work remains uncommitted.

Gitleaks also scanned the decompressed 2026-10-06 Mac evidence and returned zero findings. Both final P5/P6 verifier source manifests match the candidate. Detailed scan reports remain outside the repository.

## 2026-10-07 提交前复核 / Commit review

- 候选扫描覆盖 2,253 个源码、文档和解压证据文件，876,457,346 字节。Gitleaks 的 257 项匹配逐行核对，全部是 `arena.py` 通过 `uuid4().hex` 生成、保存在 runner steps 中的派发 `token`，没有发现实际凭证。
- 附加证据检查的 18 项匹配均已分类：14 项是上游 benchmark 的通用 Docker 用户路径，4 项是 Windows 版本号而非有效 IP 地址；没有未解释的隐私命中。
- Mac Office 归档包含合成内容、文件哈希及编辑区诊断，排除账户、收件箱、近期文档、作者元数据和锁文件。原始 Office 文件、API 配置及详细扫描报告留在仓库外。
- 本轮主机隔离回归 293/293；Office 六份文件检查通过，两个复制文件反例均被拒绝。Windows 292/292 是前一轮结果；本次没有重跑 Windows 原生验收。

The candidate scan covered 2,253 files and 876,457,346 decompressed bytes. All 257 Gitleaks matches were verified as random dispatch UUIDs in runner steps. Additional matches were 14 generic benchmark Docker paths and four Windows version strings, with no unresolved privacy findings. Office evidence excludes account/inbox/recent-file data, author metadata and lock files. Host regression passes 293 tests; all six Office files pass and two disposable-copy mutations are rejected. The Windows 292-test result is historical. Detailed scanner reports and private configuration remain outside the repository.

## 2026-10-08 P7 / Office pilot 提交复核

- 扫描新增/修改候选的 185 个源码、文档、证据及 Office 文件解包项，共 891,172 字节；Gitleaks 未检出密钥。附加证据检查未发现个人主目录、邮件、密钥前缀、Bearer 凭证或私钥。
- 四个 2026-10-08 证据目录的 100 项归档字节哈希全部通过。截图仅自有合成窗口；Office 输入仅合成报告、支出与空白文件。原始题目里的通用 Windows User 路径保留，归档中的本机项目绝对路径规范化为 PROJECT_ROOT。
- 本轮提交前主机回归 373/373；Windows 最新同轮回归 373/373。Mac 输入零派发拒绝、Office 三题未开始及历史失败均保留，没有将单元测试/初始化计为 GUI 成功。
- API 配置、VM 凭据、编译缓存及详细扫描报告留在仓库外。WindowsWorld 原始三题、judge 参考与 Apache-2.0 许可随代码保留。

The P7/Office candidate review scanned 185 source/document/evidence entries, including extracted Office XML, totaling 891,172 bytes. Gitleaks and additional evidence patterns found no credential or unresolved personal-data matches. All 100 archive byte hashes passed. Screenshots and inputs are owned synthetic fixtures; the local project path is normalized in published preparation metadata. Host and Windows regressions each pass 373 tests, with zero-dispatch/blocked outcomes kept separate from GUI success. Private configuration, VM credentials, caches and detailed reports stay outside Git; pinned upstream task records, judge reference and license remain included.
