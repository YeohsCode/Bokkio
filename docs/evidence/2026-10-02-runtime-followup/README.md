# Runtime follow-up evidence

Environment: the existing Fusion Windows 11 IoT Enterprise ARM64 VM, x64 CPython 3.12.13, xa11y 0.15.0 and comtypes 1.4.17. Only disposable native fixtures and a newly created Notepad process were edited.

- [interactions-summary.json](interactions-summary.json): 50 native records; three input, scroll and Notepad rounds passed.
- [interactions.json.gz](interactions.json.gz): native before/after states, scroll positions and content changes, read-only rejection, dropdown/tree actions, duplicate reorder, rebuilt-ref rejection and 1,000-row coverage.
- [interaction-fixture.json](interaction-fixture.json): a native fixture snapshot before the acceptance sequence.
- [decision-runtime.json](decision-runtime.json): five native actions selected by a scripted offline provider, plus a stale-decision rejection. This is not real Jev model evaluation.
- [pytest.log](pytest.log): Windows isolated tests.
- [benchmark.json](benchmark.json): three runs at 50/100/300/1,000 content controls; excludes CLI startup.
- [jev-fixture.json](jev-fixture.json): the selected native window used for offline model evaluation.
- [jev-cases.json](jev-cases.json): five expected decisions for future real API evaluation. Saved refs are used only with the associated saved snapshot.

See [the report](../../RUNTIME-FOLLOWUP.md) for pending macOS and real Jev checks.
