# 2026-10-03 Windows Office prerequisites

- `inventory.json`: installed app/path inventory; no Office suite or mail client.
- `stage-resume/summary.json`: real Planner/Jev/UIA pause after two completed stages; one remaining write on resume.
- `stage-resume/paused.json.gz`, `resumed.json.gz`: full native/model/action traces, including historical receipts and fresh final observation.
- `file-roundtrip/summary.json`: three independent deterministic native save/reopen checks.
- Each `file-roundtrip/round-*` directory contains full actions and final native snapshot as gzip, plus the actual Notepad-saved text artifact as gzip, preserving its original bytes and hash.
- `tests.log`, `host-tests.log`: 114 isolated tests passed on each platform.

These checks do not constitute full Office workflow acceptance or official benchmark scores. The file roundtrip uses deterministic native actions; the stage recovery test uses the real Planner and Jev. Setup and evaluator code does not write the deliverable files.
