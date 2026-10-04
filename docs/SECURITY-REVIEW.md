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
