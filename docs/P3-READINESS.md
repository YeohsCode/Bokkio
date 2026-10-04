# P3 Windows UIA preparation

Date: 2026-10-01

Setup update: 2026-10-02 (Asia/Shanghai)

## Status

Installation, autonomous password provisioning and Windows development setup are complete in `Bokkio Windows Unattended`. Authenticated guest operations work. The fixed WinForms fixture and Notepad, Explorer, Settings, and Edge passed UIA reads; three native action sequences and four scale benchmarks passed. All 34 Windows unit tests passed. Results and limitations are in [P3-REPORT.md](P3-REPORT.md).

A startup check found that the first desktop used a temporary Windows profile. The x64 interpreter was moved to `C:\BokkioWorkspace\tools\python`, the environment was made independent of the temporary profile, and a targeted startup repair recreated the account profile. Windows automatically logged in after reboot with `C:\Users\Bokkio`; one-time automatic login was disabled again. Final native verification after restart passed: 34 unit tests, the five-app matrix, and three fixture action sequences. The permanent profile status is normal (0), the desktop launcher exists, and the registry password is absent.

## Selected Mac VM environment

The selected route is VMware Fusion Pro on this Mac, with a Windows 11 ARM64 guest. The host has an Apple M4 Pro, 64 GiB RAM, and approximately 201 GiB free disk space at the setup check. Guest settings have been applied and read back in Fusion: 4 virtual CPUs, 8 GiB RAM, and a 100 GB NVMe disk with pre-allocation disabled.

Fusion is free for all use cases, but its official download requires a Broadcom account. The user completed registration, sign-in, and the additional Trade Compliance and Download Conditions form, and explicitly approved the displayed download Terms and Conditions. The official file is `VMware-Fusion-26H1u1-25689522_universal.dmg` (497.25 MiB), build 25689522, released September 3, 2026. The completed download is 521,403,629 bytes; its SHA-256 matches the official value `df1911f8de651818a43c20ca1054403da7e39534f15a2e0e0f9d41ffcf728ab8`. Fusion is installed at `/Applications/VMware Fusion.app` (app version 26.0.1, build 25689522). See the [official download instructions](https://knowledge.broadcom.com/external/article/368667/download-and-license-vmware-desktop-hype.html).

The user completed virtual TPM password setup and saved the VM at `/path/to/Windows11.vmwarevm`. UEFI and Secure Boot were enabled during creation. The first boot showed no installation media; the empty VM was powered off to configure its resources. **The original VM is preserved separately; testing now uses the unattended VM described below.** A local transfer archive containing the project sources, tests, verification scripts, and vendored WinForms fixture has been prepared at `/tmp/Bokkio-windows-setup.zip`; regenerate it after further project changes.

The user completed Microsoft evaluation registration. Its redirected download page returned “We are currently experiencing high demand”; retrying the explicit `en-us` route in Chrome produced the same result. Separately, the current [standard Enterprise download page](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise) links to an `x64FRE` ISO. The earlier plan assumed an ARM64 Enterprise evaluation download from that page, but that link has not been established.

The working download route is now [Windows 11 IoT Enterprise LTSC 2024 evaluation](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-iot-enterprise-ltsc). Microsoft documents ARM64 support, a 90-day evaluation, and use in a VM. The [Microsoft download redirect](https://go.microsoft.com/fwlink/?linkid=2269595) resolves to its official `software-static.download.prss.microsoft.com` server and returns HTTP 200 for `26100.1742.240906-0331.ge_release_svc_refresh_CLIENT_IOT_LTSC_EVAL_A64FRE_en-us.iso` (5,042,194,432 bytes). The download is complete. Its SHA-256 is `3dcdba9c9c0aa0430d4332b60c9afcb3cd613d648a49cbba2d4ef7b5978f32e8`. The exact file size and four 64 KiB ranges (start, end, and two intermediate offsets) match a fresh HTTPS read from the official server. The independent full-server hash read was stopped because it was slow; a full match with the current server bytes has not been established.

The linked PDF lists SHA-256 `CCEC358A760C3C581249F091ED42D04F37B2B99C347B7A58257C3CC272D7982C`, published in Microsoft's [evaluation hash document](https://go.microsoft.com/fwlink/?linkid=2272287). This differs from the downloaded 26100.1742 refresh. A [Microsoft Q&A report](https://learn.microsoft.com/en-ca/answers/questions/2181328/%28issue%29-broken-windows-11-iot-hashes-pdf-link) reports the same actual hash for the official ARM64 download. The PDF appears to describe earlier media; this is an inference, not a matching published hash. Record the discrepancy rather than claiming PDF verification. The ISO is attached, and Setup boots successfully. The evaluation is time limited; Fusion being free does not grant a permanent Windows license. Applicable installation terms must be confirmed during setup. Label future UIA results with the actual IoT Enterprise LTSC 2024 edition and build; these do not validate newer standard Enterprise desktop versions.

The xa11y 0.15.0 Windows Python wheel is `win_amd64`, so the initial test environment needs **x64 Python inside the ARM64 guest**, using Windows' x64 application emulation. Native ARM64 Python cannot load that wheel. Confirm the interpreter architecture and successful xa11y import before running the harness. Label results as Windows ARM64 with x64 Python emulation; they do not establish performance on a native x64 Windows machine. See the [xa11y release metadata](https://pypi.org/pypi/xa11y/0.15.0/json) and [Microsoft emulation documentation](https://learn.microsoft.com/en-us/windows/arm/apps-on-arm-x86-emulation).

Run Bokkio and its UIA backend **inside the Windows guest**. The Mac accessibility tree for the VM window cannot replace the guest's Windows UIA tree. Keep the test focus on the WinForms fixture, Notepad, Explorer, and Settings; Edge remains a compatibility sample.

## Setup on Windows

Use an interactive desktop session, Python/uv, and a .NET SDK that can build the vendored `net8.0-windows` fixture. Transfer the repository plus `vendor/xa11y/test-apps/winforms/` (the vendor directory is ignored by Git).

In PowerShell, from the repository root:

```powershell
uv sync --group test --python cpython-3.12.13-windows-x86_64-none
dotnet build vendor/xa11y/test-apps/winforms/xa11y-winforms-test-app.csproj -c Release
```

Launch `vendor/xa11y/test-apps/winforms/bin/Release/net8.0-windows/xa11y-winforms-test-app.exe`. Open Notepad, Explorer, Settings, and Edge. Run `uv run bokkio apps --json` to obtain exact names or PIDs, then substitute them below:

```powershell
uv run python scripts/verify_windows.py --output evidence/windows --read-app NOTEPAD_PID --read-app EXPLORER_PID --read-app SETTINGS_PID --read-app EDGE_PID
```

Without `--read-app`, the script tests only the fixed fixture. That is a preliminary check, not the full P3 application matrix. The script does not install a VM, connect to a remote host, or handle elevation.

## Mapping and differences to validate

The following are expectations from the local xa11y provider sources, **not Windows measurements**. Sources: `vendor/xa11y/xa11y-windows/src/uia.rs`, `vendor/xa11y/xa11y-macos/src/ax.rs`, and the WinForms/Cocoa fixture sources.

| Topic | Source-level difference | Normalization / live check |
|---|---|---|
| Role | UIA ControlType versus AX role/subrole | Verify normalized role and preserve provider attributes |
| Name | UIA Name versus AXTitle/AXDescription and static text value | Use current role/name selectors; test localization |
| Native identity | UIA HWND/AutomationId versus AXIdentifier | Preserve native ID; structural refs still need invalidation rules |
| Application root | Windows synthesized process root versus macOS app AX element | Use `App.as_element()` and verify parent/ref consistency |
| Click | Invoke/Toggle/SelectionItem/ExpandCollapse patterns versus AXPress | Require advertised click and read back task outcome |
| Text write | UIA ValuePattern versus AXValue string | Verify exact resulting value; report unsupported controls |
| Typing | Windows ValuePattern splice at caret versus macOS AXSelectedText | Clear input for deterministic tests; use `--expect-value` |
| Selection | UIA SelectionItem versus AXSelected; radios use semantic press | Verify selected or checked state according to role |
| Focus | UIA SetFocus versus AXFocused | Verify focused state on actual input |
| Scrolling | Windows ScrollItem.ScrollIntoView versus macOS scroll-bar numeric positioning | Current directional CLI implementation is macOS only; establish Windows semantics before enabling |
| Tables | WinForms DataItem + TableItem can represent a cell | Verify table/row/cell role differences against the native grid |
| Visibility | UIA IsOffscreen versus AX visibility/bounds | Record results for clipped and virtualized controls |

## Runtime checkpoint

Completed: the five-app read matrix, three fixture action sequences, stale-ref handling, a measured cross-platform mapping, and native scale benchmarks at 50/100/300/1,000 content controls. The report separates total tree nodes from content counts and excludes CLI startup from benchmark timings.

Remaining runtime coverage: Windows directional scrolling, empty UIA value ambiguity, Notepad writable controls, provider action advertisement, nested window filtering, and virtualization/reordering. P4 Jev integration follows this measured cross-platform checkpoint in PLAN.md.

## Installation checkpoint

The user completed OS installation and restored guest input focus. CUA successfully advanced the first-run network page using the displayed offline option (the virtual network driver is not yet installed) and entered the local test account name `Bokkio`. This original VM was left at password creation. The user later requested autonomous provisioning; installation and password creation have now completed in the separate unattended VM. Guest setup and the Windows UIA matrix have completed in the unattended VM.

The guest bootstrap script at `scripts/bootstrap_windows.ps1` verifies official archive hashes, uses ARM64 .NET 8.0.425 and uv 0.12.21, installs x64 CPython 3.12.13, runs 34 unit tests, and builds both native fixtures. Its first run revealed PowerShell 5.1 treating native stderr progress as an error. The script now checks exit codes explicitly; setup and tests succeeded. Fixed guest tools and project directories are under `C:\BokkioWorkspace`. `Open-Bokkio.cmd` and the public desktop shortcut open the prepared development shell.

## Unattended deployment route (2026-10-02)

The user explicitly requested autonomous Windows password creation and storage on the Mac. A separate VM named `Bokkio Windows Unattended` was created through Fusion CLI with 4 CPUs, 8 GiB RAM, 100 GB NVMe, UEFI Secure Boot, and NAT. It uses the IoT LTSC optional hardware profile without vTPM ([Microsoft requirements](https://learn.microsoft.com/en-us/windows/iot/iot-enterprise/Hardware/System_Requirements)); it does not validate a standard Windows 11 hardware profile. Its private installer includes a Microsoft unattended local-account configuration, official VMware drivers and development tool archives, and a temporary guest test runner. Windows installation completed. Successful guest authentication verified the assigned password for `BOKKIO-WIN11\Bokkio`. The guest reported an active desktop session, an enabled local administrator account, Windows build 26100, and disabled automatic login with its registry password removed. Development setup and UIA validation completed. Reboot verification passed with the permanent user profile and fixed development tool paths.

The original encrypted VM remains separate. Its CLI required an encryption password; retrieving the saved key required interactive Mac authorization. On the new ARM guest, VMware Tools 13.1.5 and authenticated `vmrun` guest operations work after installation and account provisioning. Initial authentication failures occurred before setup finished; they do not establish an ARM guest-operation limitation. The temporary runner uses only the Mac VMware private interface and a task-specific token. It was stopped after verification; the guest helper, task-specific configuration, and scheduled tasks were removed. Credentials and installer payloads are stored outside the repository under a private Mac directory.
