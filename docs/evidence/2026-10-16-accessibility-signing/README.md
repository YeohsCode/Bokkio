# Accessibility authorization and executable identity

The user's normal installed app showed **application authorized, runtime unauthorized**. The macOS TCC log confirmed that the responsible process was Bokkio and the accessing process was its bundled Python. TCC rejected bundle validation of that Python with `-67056` (`errSecCSResourcesNotFound`). `codesign --verify --deep --strict` failed for the installed application with the same missing-resource-seal condition. The app retained Electron's linker signature instead of a completed Bokkio bundle signature. The previous path-help change did not fix this executable identity failure.

## Changes

- macOS packaging explicitly signs the complete app and nested code with the local ad-hoc identity, uses the Bokkio bundle identifier, and enables strict signature verification. It no longer silently ships the unsigned bundle when no Developer ID identity is installed. A release signing certificate can be selected with electron-builder's `mac.identity` override; this local build does not claim Developer ID signing or notarization.
- Runtime startup, the Harness/MCP environment, staged-runtime validation and code workers disable bytecode writes. This prevents normal Python imports from modifying the sealed application resources. A real code-worker regression imports a module and verifies that no bytecode cache is created.
- The installed-package audit requires valid app and native executable signatures on macOS, including Python, recorder, input and capture helpers, in addition to comparing packaged sources to the checkout.
- Settings distinguish a host/runtime identity mismatch from a missing user grant. The user is not told to repeat an already completed host authorization when the execution process is the failing identity.

## Validation and current limit

The installed app and native executables pass strict signature verification, including after startup through the normal application launcher. Source/package comparisons pass. TypeScript/Vite and seven Electron tests passed. The Python regression suite passed **726 tests**.

The first signed build's normal startup requested OS Keychain confirmation to read Bokkio's existing encrypted provider credential. That protected system window is unavailable to computer automation. The user has been asked to confirm it. The final signed package is installed and the pending confirmation refers to the same Bokkio credential use. No native session, desktop action, or Outlook result is claimed as verified while this confirmation is pending. A successful UI test run from an already authorized development host would not establish that normal installed-app authorization works.

- [Observed failure and pending live verification](report.json)
- [Installed-package audit after normal startup](package-audit-after-launch.json)
- [Application signature](app-signature.txt)

References: [Apple code-signing tasks](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Procedures/Procedures.html), [Apple TN2206](https://developer.apple.com/library/archive/technotes/tn2206/).
