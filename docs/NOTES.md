# P0 API Design Notes

Sources were read locally at the commits listed in `docs/P0-VERIFICATION.md`. `agent-desktop`, `computer-use-jev`, and `computeruseprotocol` were cloned to `/tmp/bokkio-p0p1-research` for research only.

## xa11y

- The Rust core exposes `App`, `Element`, `Locator`, role/name/value/description, normalized state, bounds, raw platform data, actions, tree enumeration, selectors, and semantic element actions.
- Selectors are CSS-like: `button`, `button[name='OK']`, prefix/contains matching, parent-child/descendant scoping, and indexed matches.
- macOS uses AXUIElement. Element verbs are semantic (`press`, `focus`, `toggle`, `set_value`, `type_text`, `select`, `expand`, `collapse`) and are dispatched through accessibility APIs rather than simulated input.
- Python binding exposes the same model and is installed as a prebuilt ABI3 wheel; Rust builds locally; Node binding is packaged separately with prebuilt native binaries.
- The public `Element.raw` mapping is deliberately provider-specific and JSON-compatible, while normalized fields remain cross-platform.

## agent-desktop

- A stateless CLI can expose observation and action commands, but action and lifecycle safety must be explicit; side effects are avoided by default.
- Snapshot output separates compact human-readable trees from structured JSON and recovery-capable error codes.
- Stable refs are treated as an identity problem, not merely an ordinal path. Native object retention can improve address stability, but stale, recreated, and virtualized controls still require explicit invalidation.
- Progressive disclosure (shallow skeleton plus focused drill-down) reduces context size in dense applications without abandoning full-tree capability.

## computer-use-jev / jev-desktop

- The decision loop is observation → small policy decision → action plus target. The policy returns an action, target, confidence, and completion signal.
- Low confidence and contradictions with the current observation must stop execution rather than continue optimistically.
- Step budgets, action history, and refreshed observations are part of the loop contract; tool errors should not erase valid state.
- This project remains read-only in P1, so only the observation/token/target shape is adopted now.

## computeruseprotocol

- CUP models a universal element as identifier, role, name/value, bounds, states, actions, attributes, platform data, and children.
- Compact encodings can reduce context significantly, but they should be lossless enough to reconstruct the selected element and action target.
- Explicit role/state/action mappings and a platform-specific data escape hatch are preferable to prematurely flattening OS differences.

## Bokkio P1 implications

- Keep the Rust-ready boundary as data: a stable ref, normalized fields, explicit nulls, state map, bounds, parent/children links, and raw platform data.
- Derive refs from application/window identity plus structural path signatures; document that UI mutations can invalidate them and require a fresh snapshot.
- Do not use ordinals alone. Include role/name and repeated-signature occurrence in identity while retaining a normalized stable hash as the public ref.
- Convert TCC failures into a user-actionable permission error before application matching or traversal.
