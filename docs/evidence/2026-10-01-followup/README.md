# Native follow-up verification — 2026-10-01

This round adds effective AX scrolling, explicit type expectations, and `structural-v2` refs. The full native harness passed three core action sequences and three scroll round trips. All 34 isolated tests pass.

| File | Content |
|---|---|
| `summary.json` | Latest five-app matrix, unique refs, label changes, raw-read checks, three core and scroll runs |
| `textedit-blank.json` | Empty TextEdit window snapshot |
| `fixture.json` | Disposable native Cocoa fixture snapshot |
| `actions.json` | Three click/write/focus/type-with-expectation/select sequences |
| `scroll.json` | Reset, three 0 → 0.25 → 0 round trips, and boundary result |
| `postcondition-mismatch.json` | Intentional type expectation failure with expected/actual values |
| `finder-stability.json` | Three separate Finder pairs, no ref additions/removals, changing label names/bounds |

Each scroll direction moved 81 content nodes and changed the AX scrollbar value. The boundary request skipped the write and returned `unconfirmed`. Finder pairs had 8/15/13 common-ref name changes but zero removed/added refs. This establishes stability under the observed label updates; it does not establish persistent identity after virtualized controls are replaced.

## Repeat

```bash
uv sync --group test
uv run python scripts/build_native_fixture.py
```

Open `/tmp/BokkioTest.app`, TextEdit, Finder, System Settings, and Safari. Create a new empty `Untitled` TextEdit window. Then:

```bash
uv run python scripts/verify_native.py --output /tmp/bokkio-evidence
```

The harness checks that the selected TextEdit text areas are empty before saving that window. Action tests modify only the fixed native fixture. It leaves Search with an appended `!` after the intentional mismatch check and leaves the main scroll area at position 0. It saves aggregate data for personal apps and raw trees only for the empty document and fixture.

The three separate Finder stability pairs were measured outside this harness; the matrix contains its own Finder pair. [Initial evidence](../2026-10-01/README.md) preserves earlier results. Windows preparation is documented in [P3 readiness](../../P3-READINESS.md); it remains unverified on Windows.
