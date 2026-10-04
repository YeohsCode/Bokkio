# Native Windows pagination evidence

- `summary.json`: two real Planner/Jev/UIA tasks, both passed with independent native state and action-order checks.
- `hidden_target_cross_app.json.gz`: full trace for Page 40 → Go → Row 997 → new Notepad.
- `next_page_target.json.gz`: full trace for Next → Row 37.
- `*-timing.json`: timings of the actual top-level native and model calls. Checkpoint time is not measured separately.
- `preflight.json`: only 25 row controls exposed per page; stale row ref rejected after changing page.
- `build.log`, `run.log`, `done.txt`: successful fixture build, task summaries and exit code.

Trace files were copied after the guest job exited. Text is normalized to UTF-8 and LF; gzip timestamps are zero. No user documents or credentials were included.

The fixture physically creates only the current page. This checks partial exposure through pagination, not VirtualizedItemPattern. The first task explicitly supplies page number 40; autonomous page-number inference is outside this test.

The final script tightens the preflight to require the specific `stale_ref` code and adds `--preflight-only`. A separate native rerun records that exact code in `preflight-strict.json`; the full model traces above precede this diagnostic-only change.

See [report](../../P5-PAGED.md) for results and reproduction.
