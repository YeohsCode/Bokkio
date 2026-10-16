# Credential startup and actual UI verification

The signed macOS application previously decrypted saved model credentials synchronously before creating its window. An OS Keychain confirmation therefore prevented the entire UI from opening. Credential storage protects the configured Provider and Jev API keys: the encrypted files are in Bokkio's local user-data directory, and Electron uses the OS credential facility to decrypt them. It is independent of macOS Accessibility authorization.

## Implementation

- Create the main window, overlay and controls before loading model credentials. Use Electron 44's asynchronous encryption availability, encryption and decryption APIs throughout, including the system-status IPC path.
- Show explicit loading, ready and retryable failure states. Settings reads, permission status and Workflow navigation remain responsive during OS confirmation. Model execution waits for credentials through both its button and keyboard shortcut.
- Serialize startup loading and configuration writes so a delayed startup read cannot overwrite a newly saved key. A failed read leaves encrypted files intact for retry.
- Continue using the OS encryption facility. No login password is requested or collected by Bokkio, and no plaintext credential storage was introduced.

## Actual UI results

**macOS, normal installed app:** `/Users/andrewyeoh/Applications/Bokkio.app` opens through the native app launcher while the credential-loading message is visible. Clicking Configuration opens the complete Settings page during that wait. A previous denied/uncompleted Keychain confirmation produced the retry state without freezing navigation. The final installed app and nested executables pass strict code-signature verification and match the current packaged source.

**Windows, packaged app:** the UI test first saved owned dummy Provider and Jev keys in the previous synchronous implementation. After upgrading, it verified that both credentials appeared as saved, and the actual Test Connection button successfully authenticated against an owned loopback HTTP fixture. It changed the Provider key through the UI, saved and tested it, restarted the packaged app, and tested the recovered key again. Both encrypted-file checks passed. No external model was called and no real user key was used.

**Remaining macOS step:** valid signatures did not refresh the stale Accessibility entry. After an app-specific `tccutil reset Accessibility com.bokkio.desktop`, System Settings requires the user's login authentication before the current app can be added again. Host and runtime are currently ungranted. Normal-launch desktop recording, a native session and the Outlook task remain unverified until that OS step is completed.

## Evidence

- [Machine-readable results](report.json)
- [Previous Windows app: save and connect](windows-before-upgrade.json)
- [Upgraded Windows app: restore, change, restart and connect](windows-after-upgrade.json)
- [Windows UI screenshot](windows-credentials.png)
- [Final macOS installed-package audit after normal launch](macos-package-audit.json)
- [Final Windows package audit](windows-package-audit.json)

Nine Electron unit tests and the TypeScript/Vite build pass. The two startup tests specifically hold decryption pending while reading Settings and permission IPC, and verify ordering against a replacement-key save. They supplement the actual UI observations above.

Reference: [Electron safeStorage API](https://www.electronjs.org/docs/latest/api/safe-storage).
