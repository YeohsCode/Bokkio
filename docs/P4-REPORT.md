# P4: real Jev decisions on native Windows UI (2026-10-02)

Subsequent bounded-context improvements and the P5 planning loop are reported in [P5-REPORT.md](P5-REPORT.md). This report preserves the initial 9/12 scale evaluation.

OpenRouter Jev is configured on the Mac and Windows VM. Five saved native cases matched their labels, five live Windows tasks passed independent outcome checks, and four native hard cases passed. The scale evaluation accepted nine of twelve development cases; three were rejected for low confidence. P4 remains in validation while platform coverage and large-tree decision coverage improve.

## Provider and private configuration

The existing Jev project supplied an OpenRouter key. Bokkio uses `typesafe/jev-1.13` through `https://openrouter.ai/api/alpha/decisions`, as documented in the [official OpenRouter Jev introduction](https://openrouter.ai/blog/insights/what-is-jev/). Direct TypeSafe access remains available but was not exercised in this evaluation.

The key lives outside the repository:

- Mac: `~/Library/Application Support/Bokkio/jev.json`, directory mode 0700 and file mode 0600.
- Windows: `%LOCALAPPDATA%\Bokkio\jev.json`; the folder grants access to Bokkio, SYSTEM and Administrators with inherited general access removed.

Environment keys override the file. An OpenRouter key cannot be routed to the TypeSafe endpoint. Tests use injected providers and make no paid API calls. The key is absent from snapshots, evidence and source files.

Windows initially failed certificate verification. The transport now loads the certifi CA bundle and keeps TLS verification enabled; real guest calls succeeded afterward.

## Decision contract

Operation and target are separate closed Choice questions. Only the chosen operation's target head is consumed. Every accepted Choice must select a current option and return a valid complete probability distribution. Its confidence must be at least 0.7. Confidence measures distribution concentration, not correctness, per the [official Choice documentation](https://docs.typesafe.ai/primitives/choice).

Goal satisfaction uses Noul with `true` and `false` criteria and no separate confidence field, matching the [official Noul contract](https://docs.typesafe.ai/primitives/noul). A reported `done` is not independent proof of task success.

More than 255 targets use groups of at most 240, followed by selection within the chosen group. Dense trees share repeated parent and kind fields, and defer target questions until the operation is accepted. This preserves all observed target labels and avoids the token-limit errors encountered in the first 1,000-control runs. It does not guarantee that arbitrary large or verbose application trees fit the provider limit.

Text comes only from caller-supplied allowed values. Model tokens map back to observed refs in code. Disabled, invisible and indistinguishable targets are excluded. Execution rereads the selected app/window scope, checks the snapshot digest and action capability, and rejects stale state before dispatch. The desktop can still change after that check; task outcome verification remains necessary.

## Live Windows outcomes

Final source version: [native-final.json](evidence/2026-10-02-jev/native-final.json).

| Task | Model actions | Independent outcome |
|---|---|---|
| Set Search | set_value | Exact field value `Bokkio Jev native` |
| Submit | click | Native status label contains submitted text |
| Expand Parent | expand | Fresh tree reports expanded=true |
| Select Second in Mode | expand → select | Fresh combo value is Second |
| Scroll content right | scroll | X position increases and 30 content buttons move left |

Five tasks passed using six real model calls. Median API time per call was 1.671 seconds; reported input tokens totaled 51,753 and cost totaled $0.002174. These figures exclude runtime observation and action time. Snapshots, model responses, actions and outcome checks are preserved in the trace.

The fixed app was reset through deterministic native actions before the tasks. Jev selected each tested action and target; setup actions are not model results. Earlier runtime evidence separately covers native collapse and repeated action replay.

## Native hard cases

Evidence: [hard-native.json](evidence/2026-10-02-jev/hard-native.json). Fixture: `fixtures/windows-jev-hard`.

| Case | Result |
|---|---|
| Same-named Action buttons in Left/Right pane | Correct Right pane button selected; native status confirms |
| Tree changes after a real model decision | Refresh replaces Old controls; old decision rejected by snapshot guard before dispatch |
| Dynamic items after replacement | New snapshot leads to Fresh 2; native status confirms |
| Deep tree | Six expansions reveal Workflow / Level 1–5; seventh action selects Leaf and status confirms |

All four cases passed. Ten real calls, including the deliberately invalidated decision, had a median API time of 2.070 seconds and reported total cost of $0.001465. The deep-tree trace preserves each observation and action.

## Saved-snapshot scale evaluation

Evidence: [scale-final-results.json](evidence/2026-10-02-jev/scale-final-results.json), with twelve labeled cases and four native snapshots under [scale/](evidence/2026-10-02-jev/scale/scale-cases.json). Each size has three targets: first, middle and last Sample button. No actions execute during this benchmark.

| Content controls | Label matches / attempts | Accepted wrong actions | Guard rejections | Median API seconds per attempt | Median reported input tokens per attempt | Reported cost, three attempts |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 3/3 | 0 | 0 | 1.180 | 8,489 | $0.001070 |
| 100 | 3/3 | 0 | 0 | 1.635 | 15,525 | $0.001956 |
| 300 | 2/3 | 0 | 1 | 2.785 | 21,740 | $0.003086 |
| 1,000 | 1/3 | 0 | 2 | 2.140 | 18,253 | $0.004256 |

Times and tokens sum completed calls within each attempt, including calls that ended in a guard rejection. Accepted 300-control decisions use two calls; the accepted 1,000-control decision uses three. Rejected attempts stop earlier, so their latency is not successful-task latency.

The 300 middle target was rejected for group confidence below 0.7. The 1,000 middle and last targets were rejected for operation confidence below 0.7. No incorrect accepted action/ref appeared in these twelve cases. Rejections count against coverage: 9/12 accepted and matched, 3/12 rejected. They are not task successes.

These are small development samples used while changing the implementation, not a held-out accuracy estimate. UIA exposes controls outside the viewport, and the model's click/scroll uncertainty contributes to the large-tree results. This benchmark checks labeled action/ref selection, not end-to-end completion on offscreen targets.

The final basic saved-snapshot evaluation also matched 5/5: [offline-final.json](evidence/2026-10-02-jev/offline-final.json).

## Verification and remaining work

- Mac: 66 isolated tests passed.
- Windows: the same 66 tests passed; [guest log](evidence/2026-10-02-jev/windows-pytest.log).
- Native hard fixture built with zero warnings and errors; [build log](evidence/2026-10-02-jev/hard-build.log).
- Windows remains ARM64 with x64 Python emulation; performance is specific to this VM and network.
- Mac foreground remains loginwindow. Real macOS horizontal scrolling and model-driven task replay await an unlocked session.
- A provider exposing only visible virtual rows remains untested; the existing owner-data ListView exposes all 1,000 rows.
- Improve large-tree coverage without lowering the confidence gate. Add viewport context, bounded target search/observation and an independent repeated evaluation set.
- Add structured blocked/error states and measured recovery policies before P5's planner and cross-application loop.

## Reproduction

```bash
uv run pytest -q
uv run python scripts/evaluate_jev.py \
  --cases docs/evidence/2026-10-02-runtime-followup/jev-cases.json \
  --output /tmp/bokkio-jev-basic.json
uv run python scripts/evaluate_jev.py \
  --cases docs/evidence/2026-10-02-jev/scale/scale-cases.json \
  --output /tmp/bokkio-jev-scale.json
```

With the disposable interactions fixture running on Windows:

```powershell
python scripts\verify_jev_native.py --output C:\BokkioTasks\jev-native.json
dotnet build fixtures\windows-jev-hard\windows-jev-hard.csproj -c Release
python scripts\verify_jev_hard.py --fixture fixtures\windows-jev-hard\bin\Release\net8.0-windows\bokkio-jev-hard-fixture.exe --output C:\BokkioTasks\jev-hard.json
```

Earlier JSON files retain development failures: combined-choice ambiguity, scroll aliases, certificate failure, and dense-tree token limits. `offline-development.json` also has an incorrect historical provider label; it used OpenRouter. Use the `*-final` files for the current implementation and retain the earlier traces to explain changes. Reported costs cover the cited final runs, not all development calls.
