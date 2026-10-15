# Desktop navigation and chat configuration UX verification

The Shortcuts library was mounted in the global layout, including Chat and Settings. Chat only loaded the desktop credential store, leaving an existing Bokkio planner credential unused on the first desktop launch. The connection-test button also ignored unsaved input, and SDK provider failures lost their actionable cause.

The library now belongs only to the Shortcuts workspace. Recording, Chat and Settings reclaim its width. Chat uses its task-history sidebar. Its composer remains visible while conversation content scrolls, including when a notification is present.

On the first desktop launch, an existing Bokkio `planner.json` OpenRouter key is copied into the desktop system-encrypted credential store. The desktop keeps its own model selection. Existing desktop settings take precedence, and deleting a saved key prevents automatic reimport. Keys from a config naming another endpoint are not imported. Jev remains independently configurable.

Without credentials, Chat offers a configuration action and preserves the typed task while navigating to Settings and back. Testing the model connection saves and uses the visible fields. Provider failures show an actionable status, including invalid keys and exhausted credits, instead of a generic missing-answer error.

## Installed application checks

| Platform | UI assertions | Actual model replies | Invalid-key failure | Package |
| --- | --- | --- | --- | --- |
| macOS ARM64 | 28 passed | 3 | HTTP 401, actionable message | installed Bokkio.app |
| Windows ARM64 VM | 28 passed | 3 | HTTP 401, actionable message | installed unpacked Bokkio.exe |

The test launches packaged applications with isolated runtime state and encrypted credential storage. It navigates and changes configuration through visible UI controls; no settings/chat API or component-state mutations are used to set up or complete these cases. Model calls use OpenRouter `z-ai/glm-5.3-flash` and request the literal reply `BOKKIO_CHAT_OK`.

Cases cover library visibility and width, missing-key configuration guidance, prompt preservation, connection testing with unsaved fields, encrypted credential restoration after restart, successful dialogue after restart, invalid-key diagnosis, deletion preventing reimport, first-launch import from local Bokkio configuration, and composer layout with notifications present. These checks target navigation and chat configuration; desktop action recording/replay results are documented separately in [the Workflow UX baseline](../2026-10-15-workflow-ux/README.md).

- Runner: [bokkio-desktop-navigation-chat.cjs](../../../../desktop/tests/bokkio-desktop-navigation-chat.cjs)
- [macOS report](macos/report.json), [Windows report](windows/report.json)
- [macOS package audit](macos/package-audit.json), [Windows package audit](windows/package-audit.json)
- [macOS successful chat](macos/chat.png), [Windows successful chat](windows/chat.png)
- [macOS setup](macos/setup.png), [Windows setup](windows/setup.png)
- [macOS provider error](macos/provider-error.png), [Windows provider error](windows/provider-error.png)

Python regression suite: **721 passed**. Electron tests: **7 passed**. TypeScript and Vite build passed. Package audits compare installed entry points, renderer manifest and runtime sources to the working tree, and check that removed video implementation/data fields remain absent.

The normal macOS installation was also opened through the desktop UI: its imported key appeared as saved in the encrypted store, the visible connection test succeeded, and the user's unsent Outlook task was restored without submission.
