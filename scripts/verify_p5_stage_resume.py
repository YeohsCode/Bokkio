"""Native Windows recovery after two verified, overwritten intermediate states."""
import argparse
import json
from pathlib import Path
import subprocess
import time

from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def verify(fixture, output):
    import xa11y
    output.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([str(fixture.resolve())])
    try:
        xa11y.App.by_pid(process.pid, timeout=20)
        time.sleep(1)
        app = str(process.pid)
        backend = Xa11yBackend()
        goal = ('In the Search field, first enter "P5 stage one", then replace it with '
                '"P5 stage two", then replace it with "P5 stage three". '
                'Use three separate subtasks, in that order, each verified by the Search value. '
                'Do not submit the form.')
        written = []
        class PauseAfterSecond:
            def snapshot(self, *args, **kwargs): return backend.snapshot(*args, **kwargs)
            def windows(self, *args): return backend.windows(*args)
            def perform(self, *args, **kwargs):
                result = backend.perform(*args, **kwargs)
                after = result.get('after') or {}
                if after.get('name') == 'Search' and result['action'] in {'type', 'set_value'}:
                    written.append(after.get('value'))
                return result
        paused = DesktopAgent(PauseAfterSecond(), OpenRouterPlanner(), JevProvider(),
                              max_actions=6, max_replans=1,
                              control=lambda: 'pause' if written and written[-1] == 'P5 stage two' else None).run(
                                  goal, [app], output / 'paused.json')
        before = len(written)
        # A new runtime reads only the durable checkpoint, using fresh UIA objects.
        fresh_backend = Xa11yBackend()
        class RecordResume:
            def snapshot(self, *args, **kwargs): return fresh_backend.snapshot(*args, **kwargs)
            def windows(self, *args): return fresh_backend.windows(*args)
            def perform(self, *args, **kwargs):
                result = fresh_backend.perform(*args, **kwargs)
                after = result.get('after') or {}
                if after.get('name') == 'Search' and result['action'] in {'type', 'set_value'}:
                    written.append(after.get('value'))
                return result
        resumed = DesktopAgent(RecordResume(), OpenRouterPlanner(), JevProvider(),
                               max_actions=6, max_replans=1).run(goal, [app], output / 'resumed.json',
                                                               resume=output / 'paused.json')
        final = flatten(fresh_backend.snapshot(app)['windows'])
        checks = {'paused_after_two_completed': paused['status'] == 'paused' and len(paused['completed_steps']) == 2,
                  'ordered_writes_once': written == ['P5 stage one', 'P5 stage two', 'P5 stage three'],
                  'resume_only_remaining_write': before == 2 and len(written) - before == 1,
                  'final_native_value': any(n['name'] == 'Search' and n['value'] == 'P5 stage three' for n in final),
                  'retained_two_historical_steps': len([e for e in resumed['events'] if e['kind'] == 'subtask_retained']) == 2}
        row = {'passed': resumed['status'] == 'completed' and all(checks.values()),
               'paused_status': paused['status'], 'resumed_status': resumed['status'],
               'actions': resumed['actions'], 'replans': resumed['replans'], 'writes': written, 'checks': checks}
        (output / 'summary.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
        print(json.dumps(row), flush=True)
        return row['passed']
    finally:
        process.terminate(); process.wait(timeout=10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.fixture, args.output) else 1)
