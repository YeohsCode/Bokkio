# WindowsWorld Microsoft Office pilot

Pinned upstream revision: `fbccd464f94fec9e284e139f97bf96d0b192f580`.
Source: `HITsz-TMG/WindowsWorld`, `benchmark.json` (181 tasks), Apache-2.0.

Three unmodified task records are preserved in `original/`:

| ID | Application | Original task |
|---|---|---|
| win_adm_l1_003 | Microsoft Word | Heading 1 title, Calibri 11pt body, 1.15 line spacing, save |
| win_acc_l1_001 | Microsoft Excel | Currency format on column D, save |
| win_pro_l1_003 | Microsoft PowerPoint | Create a title slide with Alpha Initiative, save Q2项目总结.pptx |

`manifest.json` pins original-task hashes, the full source benchmark hash, app names and the L1 15-step budget. `judge-rubric.json` preserves the original evaluate() system prompt, model and endpoint. `upstream-evaluate.py.txt` is an attribution/reference copy, not an imported executable. The original license is included.

This is a **Mac environment adaptation**, not an official leaderboard result. Setup maps desktop paths to isolated task folders, generates deterministic Word/Excel input content from upstream prompts, and supplies a zero-slide PowerPoint scratch document in the isolated desktop to avoid recent-file context and initialize the Save As directory. It contains no title slide or answer. Setup opening is reported separately from Agent actions. Neither input generation nor a manually edited evaluator fixture counts as Agent execution. The requested PPT output is absent at setup.

Run from the repository:

```sh
uv run python scripts/office_pilot.py prepare --workspace /tmp/bokkio-office-new
uv run python scripts/office_pilot.py run --workspace /tmp/bokkio-office-new
uv run python scripts/office_pilot.py evaluate --task win_adm_l1_003 --artifact /tmp/bokkio-office-new/win_adm_l1_003/desktop/季度报告草稿.docx
```

`run` uses DesktopAgent with the existing Planner/Jev. PowerPoint has scoped local OCR for its declared title placeholder while menus/dialogs stay native; Office combo input uses captured bounds with native identity/focus checks. Current native input passed 3/3 in fresh fixture processes. Full Office development rounds r28 and r30 each passed 3/3. The latest completed round r33 passed 0/3; three consecutive 3/3 rounds remain pending. Live acceptance is paused for the requested code snapshot. Word selection targets are derived from the pilot’s declared first-paragraph/body structure and current native text; inserted selections remain counted Agent actions. Exact source/output paths bind authorized documents; opening a second unbound PowerPoint presentation is excluded. Environment preflight and task failures are retained. Local read-only OOXML grading verifies saved formatting/content; original VLM grading is optional through `judge` and requires `QWEN_API_KEY`. Both are explicitly labeled as adaptations. No outgoing mail task is selected, and app actions that share/send/publish are refused.

See [latest progress](../../docs/evidence/2026-10-10-office-progress/README.md) for actual task results and remaining acceptance work, and [readiness report](../../docs/OFFICE-PILOT-READINESS.md) for the original prerequisites.
