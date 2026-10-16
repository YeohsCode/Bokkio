# macOS Accessibility setup UX

The native adapter previously returned a generic host-or-Python error with no paths and unconditionally required restarting. Desktop settings checked only Electron's permission state, not the runtime that performs native work.

The installed app now passes its application path through the service, Harness and MCP subprocess environment in both Jev modes. Permission errors name the application and actual resolved Python executable. Settings display these paths, separate application/runtime permission checks, copy and Finder actions, an explicit system authorization request, correctly quoted shell commands, and automatic status refresh when returning from Settings. Chat and Recording show a direct setup entry while native access is missing, without blocking ordinary conversation.

The helper [bokkio-macos-permissions.command](../../../scripts/bokkio-macos-permissions.command) opens Privacy & Security / Accessibility and selects the installed app in Finder. It does not reset existing permissions or write the TCC database. Explicit invalid application paths fail instead of silently selecting another installation.

## Real installed-app verification

Native UI actions were performed against `/Users/andrewyeoh/Applications/Bokkio.app`, launched through the normal application launcher. Settings showed both complete paths and both processes as unauthorized. The copy button returned its success notice. The Chat permission banner showed the app path. A real chat task requested exactly one `session.open` permission self-check and no desktop actions. Its actual MCP error contained the app and Python paths, helper commands, and conditional restart instructions, demonstrating that the path survives the real SDK/MCP subprocess chain.

The helper script was executed with that install path. Finder visibly selected `Bokkio.app` in the user's Applications folder, and System Settings showed its authentication sheet. The app's authorization button also opened the system permission flow. The OS password confirmation is still pending; this report does not claim Accessibility was granted or Outlook automation succeeded.

See [the recorded checks and actual tool error](report.json) and [installed-package source audit](package-audit.json). User mail content and credentials are not included.

Python regression: **725 passed**. Electron tests: **7 passed**. TypeScript/Vite and shell syntax checks passed. Automated checks cover exact-path errors, CLI fallback, app-identity propagation with Jev on/off, and safe quoting of shell metacharacters.

## Platform references

- [Apple: allow Accessibility apps to access your Mac](https://support.apple.com/guide/mac-help/mh43185/mac)
- [Apple: AXIsProcessTrustedWithOptions](https://developer.apple.com/documentation/applicationservices/1459186-axisprocesstrustedwithoptions)
- [Electron: isTrustedAccessibilityClient](https://www.electronjs.org/docs/latest/api/system-preferences#systempreferencesistrustedaccessibilityclientprompt-macos)

The local macOS `man tccutil` documents `reset` as its supported command. No `grant` command is provided by that utility.
