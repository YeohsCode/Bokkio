# P2 Report: Unified Elements and Native macOS Actions

Date: 2026-10-01

Runtime: `xa11y==0.15.0`, native Cocoa fixture `BokkioTest`.

## Result

Three complete native action sequences passed again through the actual Bokkio CLI. Each run clicked Submit and checked the status label, cleared Search, focused it, typed a distinct value with `--expect-value`, and selected a table row. Three additional scroll round trips each changed the scrollbar 0 → 0.25 → 0 and moved 81 content nodes in both directions. At the upper boundary, an upward request correctly returned `unconfirmed` with reason `at_boundary`.

An intentional text expectation mismatch returned `unconfirmed` with expected/actual values. The final UI was independently observed through Computer Use: Status Ready, Search `Bokkio native run 3!` after the mismatch probe, Item 2 selected, Fruit Banana, and scroll position 0.

Core macOS P2 acceptance now includes effective vertical scrolling through exposed numeric AX scroll bars. Horizontal directions have isolated coverage; a live horizontal fixture remains pending. Windows support is unverified.

## Implemented

- Unified nodes expose `platform`, role/name/value, state, bounds, parent/children, normalized `actions`, structural `ref`, and retained native attributes. `structural-v2` stabilizes unique passive label refs while keeping interactive names in identity.
- Selector priority is exact ref, then role/name with optional parent ref. Missing, stale, ambiguous, and contradictory selectors return structured errors with candidate summaries. An exact stale ref does not fall back to another target.
- Actions resolve against a freshly read live tree, call the native element, and read the tree again. Disabled targets and unadvertised clicks are rejected before execution.
- `set_value`, `focus`, and `select` check their direct postconditions. Radio selection uses `press()` and checks `checked`; table rows use `select()` and check `selected`. Type can check an explicit `--expect-value`. Click and type without an expectation return observations; a task must check its own successful outcome. Missing targets after checked actions return `unconfirmed`. `tree_changed` alone is not a success condition.
- Application snapshots, window snapshots, and window enumeration share refs. Same-signature siblings receive distinct occurrence-based refs.

## Actual action support

| CLI action | Native call | Observed result |
|---|---|---|
| `click` | `press()` | Submit toggled its status label in each of three runs; OK enabled Cancel during exploratory testing |
| `invoke` | `press()` | Alias of click; no separate live alias invocation |
| `set_value` | `set_value(value)` | Search cleared in all three runs; Fruit changed Apple → Banana, readback `confirmed` |
| `type` | `type_text(value)` | With `--expect-value`, Search matched `Bokkio native run 1/2/3`, `confirmed`; an intentional mismatch returned `unconfirmed` |
| `focus` | `focus()` | Search's focused state was true, `confirmed`, in all three runs |
| `select` | `select()` for rows, `press()` for radios | Alternating table rows became selected, `confirmed`; radio checks Option B → Option A → Option B all returned checked `on`, `confirmed` |
| `scroll` | Selected AXScrollBar `set_numeric_value()` | Three live vertical round trips confirmed numeric movement and 81 moved content nodes; boundary returned `unconfirmed` |

The radio fixture does not enforce mutual exclusion between Option A and Option B. These checks verify the target checked state; they do not establish exclusive-group behavior.

Typing follows the current text selection. An exploratory input replaced selected text; it is not guaranteed to append. Setting a combo box's text value does not establish popup-item selection or callback behavior.

## Three-run evidence

| Run | Status after Submit | Search value after typing | Selected Items row |
|---|---|---|---|
| 1 | Ready | Bokkio native run 1 | Item 2 |
| 2 | Submitted | Bokkio native run 2 | Item 1 |
| 3 | Ready | Bokkio native run 3 | Item 2 |

This verifies a repeated CLI action sequence against a fixed native application. Recorder and saved Workflow replay remain later phases.

The initial direct `select()` call on Option B was a silent no-op. The adapter now maps radio selection to advertised `press()` and verifies `checked == "on"`.

Live failure checks passed for stale ref, ambiguous text field selector, and an unadvertised click on Notes. Scroll amount, unsupported axes, ambiguous bars, nested containers, native no-op behavior, and boundaries are covered by isolated tests; the boundary was also tested live. Isolated tests additionally cover contradictory selectors, disabled targets, repeated writes, duplicated sibling refs, and native window IDs reused across windows.

## Unified mapping

| Field/action | xa11y source |
|---|---|
| `platform` | Host platform label |
| `role`, `name`, `value`, `state`, `bounds` | Element properties |
| `actions` | Normalized native verbs plus radio selection and numeric scroll-bar capabilities; original verbs retained |
| `parent`, `children`, `ref` | App-root traversal and structural path |
| `platform_data` | `Element.raw`, description, actions, stable ID, scroll-bar numeric value |
| `click`, `invoke` | `Element.press()` |
| `type`, `set_value` | `Element.type_text()`, `Element.set_value()` |
| `select`, `focus` | `Element.select()` for rows, `Element.press()` for radios, `Element.focus()` |

## Scroll semantics

`--direction up/down/left/right` is required. `--amount` is a fraction of the full normalized scroll range in `(0, 1]`, default 0.25; it is not a page count. Bokkio resolves a scroll bar directly or through the closest containing AXScrollArea, excludes nested scroll areas when choosing its bar, requires exactly one bar on the requested axis, and checks a numeric 0..1 position. It clamps the requested destination to the range. Unsupported or ambiguous targets fail before mutation.

The result reports the bar and scope refs, before/requested/after positions, moved-content count, and a reason. `confirmed` verifies scroll position movement in the requested direction. Content displacement is separate evidence; the live harness asserts it as well. At a boundary the native write is skipped and the result is `unconfirmed`. This implementation uses native AX numeric values, with no mouse wheel simulation.

The xa11y `scroll_into_view()` macOS method remains a no-op and is unused. The fixture advertised page-scroll verbs, but an exploratory call returned AX error -25205. Bokkio therefore uses the numeric bar path. This is directional scrolling, not automatic scroll-to-element.

## Validation and pending work

`uv run --group test pytest -q`: **34 passed**. Coverage includes schema, selectors, actions, real-API regressions, radio semantics, explicit type expectations, missing targets after actions, directional scrolling, numeric no-ops, boundaries, nested/ambiguous scopes, invalid amounts, and dynamic-label refs.

The updated live harness passed three core sequences and three scroll round trips. Finder ref sets remained stable across three separate snapshot pairs while labels changed. The Windows harness parser and macOS guard were checked; it has not run on Windows.

Latest evidence: [summary](evidence/2026-10-01-followup/summary.json), [action traces](evidence/2026-10-01-followup/actions.json), [scroll traces](evidence/2026-10-01-followup/scroll.json), [intentional value mismatch](evidence/2026-10-01-followup/postcondition-mismatch.json), and [Finder ref measurements](evidence/2026-10-01-followup/finder-stability.json). Fixture setup: [verification guide](evidence/2026-10-01-followup/README.md). [Initial evidence](evidence/2026-10-01/README.md) preserves the combo and radio checks and earlier permission/scroll behavior.

Next: run Windows UIA acceptance using [the prepared environment brief](P3-READINESS.md). Extend macOS coverage for live horizontal scrolling, containers without exposed numeric bars, and virtualized/reordered trees. Jev follows the cross-platform runtime checkpoint; planning, recording, and visual fallback remain later work.
