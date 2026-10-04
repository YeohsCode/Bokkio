# Native variation evidence

Preserves initialization failures, all completed attempts, the v4 interruption, input setup, independent oracles, native intermediate checks, checkpoints, fresh-process reopening and deliverable bytes. These are WAA-derived development fixtures, not official benchmark scores.

- Full six-fixture rounds: v2 2/6, v3 3/6, v5 5/6.
- v4 completed 0/1, interrupted the second task after 29 actions and left four tasks unstarted.
- Targeted v6: 3/3. v7: 0/1. Final PNG v8: 1/1.
- Requirement change v1: 0/1 (one of two versions started); v2: 2/2; v3: 0/1 (one of two started); final v4: 2/2.
- Final host and Windows regression checks: 195 each.

`run-index.json` preserves denominators and source hashes; `failure-index.json` retains failures. Raw JSON is normalized to UTF-8/LF and large traces are compressed with deterministic gzip timestamps. Deliverable gzip files retain the exact persisted bytes; their hashes are checked against result rows. Source text bytes remain unchanged inside gzip archives; console logs use LF with trailing whitespace removed. `checksums.json` hashes the archived files. Source hashes on final requirement-change v4 match the published code; earlier rounds deliberately retain their original hashes. The final combined fixture coverage comes from different versions and is not a single 6/6 round.

No private API configuration or VM credentials are included. See the privacy review and P5 report for scope and limitations.
