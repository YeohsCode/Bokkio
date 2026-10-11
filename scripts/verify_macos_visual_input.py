"""Real Jev/Agent visual input on three fresh, owned painted Mac windows.

The two subtask contracts are fixed; Jev chooses observed targets. Business
state is independently read from the fixture, not inferred from input receipts.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.office_runner import input_environment
from bokkio.visual_runtime import HybridBackend, MacVisionProvider, VisualPolicy, WindowScope
from bokkio.workflow import save_json
from bokkio.xa11y_backend import Xa11yBackend


def run(fixture, output):
    output.mkdir(parents=True, exist_ok=False)
    report = {'scope': 'owned_macos_visual_input_fixed_subtasks_real_jev',
              'environment': input_environment(), 'planned': 3, 'rounds': []}
    save_json(output / 'summary.json', report)
    if not report['environment']['ready']:
        report.update(status='blocked',started=0,passed=None,reason=report['environment']['reason'])
        save_json(output / 'summary.json', report)
        print(json.dumps({'status':'blocked','reason':report['reason'],'started':0}),flush=True)
        return report
    for index in range(1, 4):
        env = dict(os.environ)
        for key in ['BOKKIO_VISUAL_DUPLICATE', 'BOKKIO_VISUAL_WINDOWS', 'BOKKIO_VISUAL_MINIMIZE']:
            env.pop(key, None)
        state_file = output / f'round-{index}.state.json'
        business_file = output / f'round-{index}.business.json'
        env.update(BOKKIO_VISUAL_STATE=str(state_file), BOKKIO_VISUAL_RESULT=str(business_file))
        process = subprocess.Popen([str(fixture / 'Contents/MacOS' / fixture.stem)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            until = time.monotonic() + 10
            while not state_file.exists() and time.monotonic() < until:
                if process.poll() is not None:
                    raise RuntimeError('Owned fixture exited before readiness')
                time.sleep(.1)
            state = json.loads(state_file.read_text())
            app = str(state['pid'])
            scope = WindowScope('macos', state['pid'], 'BokkioVisual', state['window_id'])
            backend = HybridBackend(Xa11yBackend(), MacVisionProvider(), {app: scope},
                                    policies={app: VisualPolicy(input_labels=('Enter code',))})
            literal = f'CODE{index}'

            class Planner:
                def plan(self, goal, observations, progress=None):
                    def step(id, goal, expected, values):
                        return {'id': id, 'app': app, 'window': scope.title, 'goal': goal,
                                'allowed_values': values, 'risk': 'local_write', 'requires_action': True,
                                'success': [{'role': 'visual_text', 'name': expected,
                                             'parent_name': scope.title, 'field': 'present', 'equals': True}]}
                    return {'goal': goal, 'steps': [step('click', 'Click Run check', 'Checked', []),
                            step('type', f'Type {literal} into Enter code', literal, [literal])]}, {}

            def final(trace):
                business = json.loads(business_file.read_text())
                return business['clicks'] == 1 and business['input'] == literal, business

            trace = DesktopAgent(backend, Planner(), JevProvider(), max_actions=4, max_replans=0,
                                 final_verifier=final).run(
                f'Click Run check then type {literal} into Enter code', [app], output / f'round-{index}.agent.json')
            business = json.loads(business_file.read_text())
            row = {'round': index, 'status': trace['status'], 'actions': trace['actions'],
                   'business': business, 'expected_input': literal,
                   'passed': trace['status'] == 'completed' and business['clicks'] == 1 and business['input'] == literal}
            report['rounds'].append(row)
            save_json(output / 'summary.json', report)
            print(json.dumps(row), flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    report['status']='completed'
    report['started']=len(report['rounds'])
    report['passed'] = sum(row['passed'] for row in report['rounds'])
    save_json(output / 'summary.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.fixture, args.output)
    raise SystemExit(0 if report['passed'] == 3 else 1)
