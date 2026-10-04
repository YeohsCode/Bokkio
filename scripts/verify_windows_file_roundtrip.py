"""Deterministic native UIA menu/dialog/save/reopen prerequisite; no model scoring."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from bokkio.model import tree_digest
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend


def verify(output, rounds=3):
    import xa11y
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for iteration in range(rounds):
        directory = output / f'round-{iteration + 1}-{uuid4().hex[:8]}'
        directory.mkdir()
        artifact = directory / 'weekly-report.txt'
        content = f'Bokkio synthetic weekly report\r\nOrders: {iteration + 1}\r\nTotal: 42'
        owned, events = [], []
        backend = Xa11yBackend()
        def start():
            process = subprocess.Popen(['notepad.exe'])
            owned.append(process)
            xa11y.App.by_pid(process.pid, timeout=20)
            time.sleep(0.5)
            return str(process.pid)
        def act(app, action, role, name, **kwargs):
            snapshot = backend.snapshot(app)
            result = backend.perform(app, action, role=role, name=name,
                                     expected_snapshot=tree_digest(snapshot['windows']), **kwargs)
            events.append({'snapshot': snapshot, 'result': result})
            return result
        started = time.perf_counter()
        try:
            app = start()
            act(app, 'set_value', 'text_area', 'Text Editor', value=content)
            act(app, 'click', 'menu_item', 'File')
            act(app, 'click', 'menu_item', 'Save As...')
            dialog_seen = any(n['role'] == 'dialog' and n['name'] == 'Save As'
                              for n in flatten(backend.snapshot(app)['windows']))
            act(app, 'set_value', 'text_field', 'File name:', value=str(artifact))
            act(app, 'click', 'button', 'Save')
            deadline = time.monotonic() + 5
            while not artifact.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
            saved_text = artifact.read_text(encoding='utf-8')
            saved_bytes = artifact.read_bytes()
            owned[-1].terminate(); owned[-1].wait(timeout=10)
            app = start()
            act(app, 'click', 'menu_item', 'File')
            act(app, 'click', 'menu_item', 'Open...')
            snapshot = backend.snapshot(app)
            dialogs = [n for n in flatten(snapshot['windows']) if n['role'] == 'dialog' and n['name'] == 'Open']
            assert len(dialogs) == 1, 'Expected unique native Open dialog'
            act(app, 'set_value', 'text_field', 'File name:', value=str(artifact))
            # Combo dropdowns also expose buttons named Open. Bind the dialog's
            # direct child, using a fresh native observation to avoid ambiguity.
            act(app, 'click', 'button', 'Open', parent=dialogs[0]['ref'])
            deadline = time.monotonic() + 5
            while True:
                snapshot = backend.snapshot(app)
                editors = [n for n in flatten(snapshot['windows']) if n['role'] == 'text_area']
                reopened = len(editors) == 1 and editors[0]['value'] == content
                if reopened or time.monotonic() >= deadline: break
                time.sleep(0.1)
            checks = {'save_dialog_seen': dialog_seen,
                      'disk_content': saved_text == content.replace('\r\n', '\n'),
                      'new_process_native_content': reopened,
                      'reopen_left_bytes_unchanged': artifact.read_bytes() == saved_bytes}
            row = {'round': iteration + 1, 'passed': all(checks.values()), 'checks': checks,
                   'actions': len(events), 'seconds': round(time.perf_counter() - started, 3),
                   'artifact': str(artifact), 'sha256': hashlib.sha256(saved_bytes).hexdigest()}
            (directory / 'final-snapshot.json').write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
        except Exception as error:
            row = {'round': iteration + 1, 'passed': False, 'error': str(error), 'actions': len(events)}
        finally:
            for process in owned:
                if process.poll() is None:
                    process.terminate(); process.wait(timeout=10)
            (directory / 'actions.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
        results.append(row)
        summary = {'scope': 'deterministic_native_prerequisite', 'rounds': rounds,
                   'attempted': len(results), 'passed': sum(r['passed'] for r in results), 'results': results}
        (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print(json.dumps(row), flush=True)
    return summary['passed'] == rounds


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if verify(args.output) else 1)
