# Real Jev evaluation evidence

Current results and limits: [P4 report](../../P4-REPORT.md).

| File | Scope |
|---|---|
| offline-final.json | Five saved native snapshots; real API, no execution, 5/5 matches |
| native-final.json | Five live Windows tasks; six Jev actions with independent outcome checks, 5/5 |
| hard-native.json | Parent context, replaced controls, stale-decision rejection and deep tree, 4/4 |
| scale-final-results.json | Twelve saved-snapshot cases at four sizes: nine matches, three low-confidence rejections |
| scale/scale-cases.json | Labels and paths to the four native Windows snapshot files |
| windows-pytest.log | 66 isolated tests passed in the guest; no real API calls |
| hard-build.log | Native hard fixture build: zero warnings and errors |

`native-final.log` and `hard-native.log` provide compact task summaries. The JSON traces retain model answers, usage, timings and runtime observations. Costs in the report count final runs only.

Earlier files preserve development iterations, including combined-head ambiguity, duplicate scroll options, TLS failure and provider token-limit rejection. The historical provider label in `offline-development.json` is incorrect: it used OpenRouter. Current files identify the provider correctly. No credentials are recorded here.

The native fixtures are disposable Windows test apps. Scale cases are development examples, not a held-out accuracy estimate or executed offscreen tasks. Mac live model testing remains pending an unlocked session.
