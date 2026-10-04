# P5 follow-up evidence — 2026-10-02

## Verified results

`summary.json` combines the latest independently verified result for each of five development cases across runs. It is not a single-run accuracy estimate.

- `extended-summary.json`, `extended.json.gz`: seven native actions across the interactions fixture, a newly owned 1,000-button scale fixture and a new Notepad. Input, submit, Sample 137, document write, Sample 619, mode selection and Sample 997 were independently checked in order. Planner scope retained 13 of 1,015 nodes. Final-source Windows run passed.
- `neighbor-summary.json`, `neighbor.json.gz`: the goal names Search without naming Submit. The planner saw nearby Submit and completed input plus submission. Scope retained 55 of 2,081 nodes. Final-source Windows run passed.
- `repeated-recovery.json.gz`: two real native field changes after Jev responses; two stale dispatches rejected, two real LLM replans, verified input/submission. Four attempts include two rejected dispatches.
- `paused.json.gz`, `resume.json.gz`: real planner/Jev calls, pause before dispatch with zero actions, same checkpoint resumed to verified native submission.
- `restart.json.gz`: owned native application restarted after Jev returned; different PID, stale decision rejected, one replan and verified right-pane button outcome.
- `checkpoint-lock.json`: a real Windows read handle briefly denies atomic replacement; retry succeeded after release.
- `host-pytest.log`, `windows-pytest.log`: final isolated regressions, 111 passed on each OS.
- `macos-final/summary.json`: actual Cocoa-control preflight failed with a repeated application root. Zero task attempts. Earlier `macos-native-preflight.json` retains the same failure before the cross-process guard regression was added.

Recovery, pause/resume and restart passed in the second development batch before nearby-control context and verified-subtask progress were added. The final batch separately verifies updated context and decision filtering through the seven-action and neighboring-control tasks. A final macOS-only guard refinement distinguishes other application PIDs and is covered by isolated tests; the native macOS preflight still fails.

## Preserved failures

- `development-checkpoint-failure.json.gz`, `.log`: first seven-action run reached the final native condition but failed while writing a checkpoint. No successful final status was recorded. The write failure coincided with copying a live trace; a unique cause was not established.
- `development-v2-summary.json`, `development-v2-extended.json.gz`: second batch passed recovery, pause/resume and restart, but the seven-action task stopped at Sample 619 due to low confidence, followed by truncated replanning. The final candidate filter fixes the unnecessary scroll alternative without lowering confidence or accepting partial output.

Full traces are gzip-compressed without dropping snapshots, model responses or native outcomes. They contain only disposable fixtures/new Notepad documents. API keys and VM credentials remain outside the repository. See [P5 follow-up](../../P5-FOLLOWUP.md) for implementation and remaining coverage.
