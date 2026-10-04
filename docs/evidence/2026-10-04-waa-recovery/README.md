# Native WAA recovery evidence

See [diagnosis and results](../../P5-WAA-RECOVERY.md). The original 15 failures remain in the previous evidence directory. Every recovery attempt is retained here.

- `run-index.json`: all rounds; v7 interrupted after two completed cases; v8 started with a brief overlap and is diagnostic only. v9 onward ran sequentially.
- `failure-index.json`: original errors and terminal status from each trace, including the interrupted partial case.
- v14 and v15 each passed 3/3; all pinned metrics and independent intermediate/final checks passed.
- `trace.json.gz`, `initial.json.gz`, `reopened.json.gz`: original bytes, gzip compressed. Other JSON/logs use UTF-8/LF; `deliverable.txt.gz` preserves original artifact bytes after decompression.
- `save-commit-probe.json`: ValuePattern and added focus both left the old filename active. `save-commit-edit-probe.json`: Win32 editing persisted 22 while preserving source bytes. Only disposable probe files were used.
- `selection.json` retains input/evaluator provenance, model settings and module hashes. Raw upstream configurations, exported metric functions and license remain in the previous evidence directory.
- `checksums.json` lists SHA-256 hashes of files in this directory. No private config or credentials are included.

These are adapted development runs in the existing ARM64 VM, not official leaderboard scores or completed WindowsWorld/OSWorld 2 evaluations.
