# Fixed Windows Agent Arena pilot bundle

These are the five tasks selected in `docs/benchmarks/windows-arena-pilot.json`
before execution. Original JSON bytes and the reviewed evaluator export are
pinned to WAA revision `6d39ed88c545a0d40a7a02e39b928e278df7332b`.

`manifest.json` records upstream paths, source SHA-256 values and downloaded
asset URLs/hashes. Assets are stored separately from runtime instructions. The
runner copies gold files into an evaluator-only cache; it never passes them to
Planner or Jev. The export contains the original `DesktopEnv.evaluate` body,
selected metrics and getters. Its hash is checked before import. WAA's MIT
license is included as `LICENSE-WAA.txt`.

Recreate with `scripts/prepare_waa_pilot.py --checkout /path/to/WindowsAgentArena
--output /tmp/waa-pilot-bundle`. New upstream revisions or changed asset bytes
require a reviewed export and new expected hashes; do not silently update them.

The Fusion Windows 11 IoT LTSC ARM64 runs adapt user paths, initial state and
controller transport. They are development results, not leaderboard scores.
