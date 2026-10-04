# Live desktop evidence — 2026-10-01

## Files

| File | Content |
|---|---|
| `summary.json` | Application counts, ref measurements, three action runs, CLI failures |
| `textedit-blank.json` | Full snapshot of a new, empty TextEdit window |
| `fixture.json` | Full native Cocoa fixture tree before the repeated sequence |
| `actions.json` | Three sequences with before/after elements and task success checks |
| `additional-actions.json` | Combo box value write, three radio selections, and explicit unsupported scroll error |
| `finder-stability.json` | Separate Finder pair, role counts and common-ref field changes |
| `safari-local.json` | Native AX controls from a disposable local HTML form |

Full trees from personal Finder windows or existing TextEdit documents are not saved. Application state and timings vary between runs. Refs include the application PID and should be reacquired after restarting an app.

## Repeat the core native verification

From the repository root, build the fixture:

```bash
uv sync --group test
uv run python scripts/build_native_fixture.py
```

This compiles the vendored `vendor/xa11y/test-apps/cocoa/main.swift` and packages `/tmp/BokkioTest.app`; it does not launch it. Open that app through Finder. Also open TextEdit, Finder, System Settings, and Safari. In TextEdit create a new empty window titled `Untitled`. Grant Accessibility to the CLI host or its exact Python interpreter if needed.

```bash
uv run python scripts/verify_native.py --output /tmp/bokkio-evidence
```

The harness changes only the native fixture: Submit, Search, and Items rows. It reads the application matrix and saves the blank TextEdit window, fixture, and action traces. The additional Safari form, Finder analysis, and combo/radio/scroll checks are separate recorded checks rather than harness outputs.

`type` inserts at the current selection; the harness first clears the field to make the expected value deterministic. Button success is checked through the status label, and table selection through the selected state. This is a native CLI sequence, not a saved Workflow engine.
