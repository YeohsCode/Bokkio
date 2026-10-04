# Office installation and native startup checks

- `configuration.xml`: actual Microsoft 365 Apps deployment configuration.
- `install-runner.ps1`: installation and exit/version collection script; run with elevation.
- `preflight.json`: initial disk and installed-product check.
- `extract.json`: official ODT/setup versions, Microsoft signature results and setup hash.
- `status.json`: installation finished with exit code 0; seven application binaries and versions.
- `uia/`: initial startup check during background installation, six reads passed and PowerPoint timed out.
- `ppt-retry/`: PowerPoint startup read passed after a longer wait.
- `final-uia/`: all seven post-install startup window reads passed; complete native snapshots are gzip files.

These are installation and startup prerequisites. Activation prompts remain; no account was signed in, no subscription or trial was started, no email was sent, and no complete office workflow was evaluated.
