# P0 Verification

Latest status (2026-10-01): Accessibility now works, live AX reads and three native action sequences passed. See the update below and the current [P1](P1-REPORT.md) / [P2](P2-REPORT.md) reports. The following 2026-09-28 record describes the original attempt.

Date: 2026-09-28  
Host: macOS 15.5, Apple Silicon. Toolchain: Rust 1.92.0, Node 25.2.1, uv 0.11.19.

## Decision

**xa11y 0.15.0 is suitable as the P1 backend API, but this workstation cannot pass P1's real-application acceptance until Accessibility permission is granted.** The macOS build, Python installation, CLI, and sample launch succeeded. Every AX read then failed with xa11y's explicit `Permission denied` error rather than returning a fake or empty tree.

## Validated

| Item | Result | Evidence |
|---|---|---|
| Repository | `xa11y/xa11y` cloned to `vendor/xa11y/` at `e81db2ec246498178a0d32c04513e75138e2b42f` | Local Git checkout |
| Rust build | Passed | `cargo build -p xa11y-test-app -p xa11y` completed in 33.45 s |
| Rust CLI | Binary built and displayed full help | `vendor/xa11y/target/debug/xa11y --help` |
| Python binding | Passed | Prebuilt `xa11y==0.15.0` wheel installed into `vendor/xa11y/.venv`; module imports and exposes `App`/`locator` |
| Sample launch | Passed | `xa11y-test-app` launched as PID 99022 |
| Selector/element API | API shape verified from local code and public declarations | `App.locator`, `Element`, role/name/value/raw/state/bounds/actions |
| Permission | **Blocked** | Both Rust CLI and Python returned explicit Accessibility denial |

Commands and exact behavior:

```text
vendor/xa11y/target/debug/xa11y apps
error: Permission denied: Enable Accessibility in System Settings → Privacy & Security → Accessibility

vendor/xa11y/.venv/bin/python (xa11y.App.list())
xa11y.PlatformError: Platform error (-1): Permission denied: Enable Accessibility in System Settings → Privacy & Security → Accessibility
```

## Installation and runtime requirements

- Rust source builds with the repository workspace; the CLI binary is `target/debug/xa11y`.
- Python installs from the published ABI3 wheel: `uv pip install --python vendor/xa11y/.venv/bin/python xa11y`.
- macOS requires Accessibility for AXUIElement. Reading window content can additionally require Screen Recording on newer macOS releases. The terminal/host or resolved interpreter must be granted permission and restarted.

The project's own `scripts/grant_macos_tcc.sh` can write a TCC row but requires sudo. Non-interactive execution failed with `sudo: a password is required`; direct user TCC inspection was also denied. No permission state was fabricated.

## Binding assessment

- **Python: available and selected for P1.** Prebuilt wheel, Pythonic API, recursive `tree()`, readable `dump()`, selector `locator()`, and JSON-compatible `raw` data.
- **Rust: build available.** The CLI and native backend build locally. It is the preferred future runtime boundary, but a Rust rewrite is unnecessary for the P1 read-only scope.
- **JavaScript: package and native target exist**, but it was not selected because Python already satisfies P1 and installing/building another binding would duplicate validation without unblocking TCC.

## Selector and operation shape

Selectors use role predicates and attribute matching (for example `button[name='Submit']`, prefix/contains matching, hierarchy, and `nth`). Element APIs expose normalized properties plus raw provider data and semantic actions. P1 deliberately uses only property/tree reads; actions are not exposed.

## Test sample checklist

| Sample | Purpose | P0 status |
|---|---|---|
| xa11y AccessKit sample | Reproducible controls: buttons, text fields, checkbox, selectors | Built and launched; AX read permission blocked |
| TextEdit | Standard AppKit text/document surface | Selected for P1; blocked by TCC |
| Finder | System shell/document browser differences | Selected for P1; blocked by TCC |
| Safari or Chrome | Web content accessibility bridge | Selected for P1; blocked by TCC |
| System Settings | Dense native settings UI and poorer AX edge cases | Retained as secondary sample |

The AccessKit sample is the fixed application required by P0. It provides deterministic controls without depending on app state.

## P1 readiness gaps

1. Real AX tree extraction remains unproven on this machine because of TCC denial. This is an environment blocker, not an xa11y capability failure.
2. App/window/tree/ref behavior across real TextEdit, Finder, and browser trees still requires measurement after permission is granted.
3. Screen Recording may be needed on this macOS version to read full window content; its absence can produce menu-bar-only trees.
4. Windows VM availability was not validated; PLAN.md permits deferring automated Windows verification outside P0.

## Reference commits

- `xa11y`: `e81db2ec246498178a0d32c04513e75138e2b42f`
- `agent-desktop`: `dcfeb737344290f62d8d1df5ad5c42646926fa05`
- `computer-use-jev`: `ff0ad8ba8e25755d37fb8d93718144c4568a596b`
- `computeruseprotocol`: `8c17e7426359242e9ca32ec91f43caba98b28040`

## Update: 2026-10-01

The historical permission blocker above is resolved. The user approved granting Accessibility to ChatGPT and the resolved uv Python interpreter; both entries were verified on. `bokkio apps` enumerated 36 applications, and full AX content was read from TextEdit, Finder, System Settings, Safari, and a native Cocoa fixture. Python Screen Recording permission was not added.

The fixed fixture for this round is built from `vendor/xa11y/test-apps/cocoa/main.swift` and packaged as `/tmp/BokkioTest.app`. Three native action sequences passed. See [P1](P1-REPORT.md), [P2](P2-REPORT.md), and [saved evidence](evidence/2026-10-01/README.md). The earlier AccessKit build remains historical build evidence. Windows environment preparation remains pending.
