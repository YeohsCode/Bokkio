# Windows UIA evidence — 2026-10-02

Windows 11 IoT Enterprise LTSC Evaluation build 26100 on Fusion ARM64, with x64 CPython 3.12.13 and xa11y 0.15.0. Native actions target only the fixed WinForms fixture. Other apps contribute read-only aggregate counts.

- `provisioning.json`: verified account, password authentication, VM resources and automatic-login cleanup; contains no password.
- `runtime.json`: actual host and interpreter architecture.
- `bootstrap.log`: verified tool installation, 34 unit tests, and both successful native fixture builds.
- `summary.json` / `matrix.json`: five-app schema/ref checks and native action count.
- `settings-windows.json`: confirms Settings is hosted by ApplicationFrameHost and exposes nested window roles.
- `fixture.json`: fixed test app tree before the final action sequence.
- `actions.json`: three runs with before/after states, exact text checks, status change and selection. Empty-text clear remains unconfirmed because the provider returns null.
- `cleanup.json`: guest tasks/helper configuration removed, automatic login disabled, registry password absent, and host runner stopped.
- `stale-ref.json`: structured missing-ref error.
- `acceptance.log`: complete successful verification trace.
- `benchmark.json`: three in-process measurements at each of 50, 100, 300 and 1,000 native content controls, with total tree counts reported separately.

These results do not establish native x64 hardware performance or writable coverage for the other apps. See [P3 report](../../P3-REPORT.md) for measured differences and limits. `profile-repair.json`, `account-after-reboot.json`, `restart-check.json`, and `persistence.log` record the successful profile repair, permanent tool paths, and repeat verification after reboot. Final summary/matrix/actions/fixture files come from that repeat run; `initial-*` aggregates retain the earlier results. The benchmark was measured before the profile repair using the same x64 interpreter version.
