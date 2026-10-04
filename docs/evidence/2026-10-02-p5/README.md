# P5 evidence — 2026-10-02

## Final results

- `scale-final.json`: 12/12 saved-snapshot goals across 50/100/300/1,000 controls; real Jev with the final compact context. `scale-bounded.json` and `scale-repeat.json` retain earlier successful repeats.
- `scale-live-final.json`: 3/3 native clicks at targets 137, 619 and 997 in an owned 1,000-button Windows fixture, checked through its status label.
- `basic-final.json`: 5/5 saved-snapshot basic goals. `native-basic-final.json`: 5/5 real Windows basic tasks, including two-step dropdown selection.
- `windows-summary.json` and `windows-task-{1,2,3}.json`: 3/3 real planner/Jev/native cross-app tasks, independently checked. `windows-live.log` contains the verifier output.
- `windows-recovery-summary.json` and `windows-recovery.json`: native state changed after Jev returned; stale execution was rejected, one real replan completed the task. Three dispatch attempts include one rejected attempt.
- `windows-pytest.log`: final isolated guest regression suite, 98 passed.
- `macos/summary.json`: actual native-control preflight failed; zero tasks attempted. `macos/initial-foreground-preflight.json` preserves the earlier foreground-only inference. `macos/session-probe.json` and `macos/native-session-diagnostic.log` confirm a locked session, granted AX permission and self-referencing native AX results. The verifier now uses actual control availability rather than the foreground name.

These are development fixtures and a small task set. Live scale and recovery evidence precede the final unrelated window-selection/context-action refinements; isolated regressions cover those refinements. The final cross-app run uses the 8,000-token planner budget. Recovery passed with the earlier 3,000-token budget.

## Preserved development failures

`development-windows-*` preserves invalid planner IDs/app keys. `schema-development-windows-*` preserves app/window mismatches. `bindings-development-windows-*` preserves a low-confidence Notepad rejection. `budget-development-windows-*` preserves incomplete planner outputs with the smaller output budget. `scale-context-development.json` preserves the first 9/12 context trial, where unrelated ancestor scroll choices did not match intended button clicks. These results are not counted as final successes.

API keys and VM credentials are stored outside the repository. Traces contain only the owned native fixtures and newly created Notepad documents. See [P5 report](../../P5-REPORT.md) for contracts, limits and commands.
