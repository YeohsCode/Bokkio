# Mac Office pilot evidence

执行开始：2026-10-06；报告完成：2026-10-07（Asia/Shanghai）。一次 CUA 原生交互流程，六份保存文件独立检查通过；不计作 Bokkio Agent 或官方 benchmark 验收。

- `artifact-verification.json`：Excel 输入、公式/缓存值，Word 段落与单页 PPT 文本；六份文件 SHA-256、字节数及三份 v1 保持不变。
- `baseline-hashes.json`：修订前的三份 v1 哈希。
- `verifier-validation.json`：正常文件通过；复制文件的缓存总额篡改、v1 字节变化均拒绝。
- `native-matrix.json`、`*-reopened-editors.json`：三款文档应用的范围受限编辑区诊断与 Word/PPT 重开后的原生文本。
- `case-results.json`：本次会话 UI 检查结果摘要，包含草稿重开及 Excel 附件抽查；没有完整 Bokkio 动作 trace。
- `diagnostics.json`：AXPress 完成未知、disabled 编辑区、Excel 观察、Outlook 深度保护和恢复记录。
- `source-hashes.json`：固定输入与验证器/原生读取代码版本。
- `checksums.json`：归档字节哈希。

原始 Office 文件及可能包含账户/近期文件的原始观察只留在本机私有测试目录。归档没有账户、收件箱、近期文件清单、作者元数据或 Office 锁文件。详情见 [报告](../../MACOS-OFFICE-REPORT.md)。

## English

One native CUA pilot, started October 6 and reported October 7, 2026. Six saved files pass independent validation and all three baseline hashes are preserved. UI checks are operator summaries, not complete Bokkio execution receipts. No application-process restart, Planner/Jev or Workflow acceptance is claimed. The Excel draft attachment was opened and checked in the UI; attachment byte hashes were unavailable. Private raw observations and Office documents are excluded from this archive.
