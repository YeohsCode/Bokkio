"""Read native Office startup windows without account or document changes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import time

from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend

APPS = ['WINWORD', 'EXCEL', 'POWERPNT', 'OUTLOOK', 'ONENOTE', 'MSACCESS', 'MSPUB']


def inventory(apps, output, startup_wait=5):
    import xa11y
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in apps:
        path = Path(r'C:\Program Files\Microsoft Office\root\Office16') / (name + '.EXE')
        process = None
        row = {'app': name, 'installed': path.exists(), 'native_read': False}
        try:
            if path.exists():
                process = subprocess.Popen([str(path)])
                xa11y.App.by_pid(process.pid, timeout=30)
                time.sleep(startup_wait)
                snapshot = Xa11yBackend().snapshot(str(process.pid))
                nodes = flatten(snapshot['windows'])
                windows = [n['name'] for n in nodes if n['role'] in {'window', 'dialog'}]
                (output / (name + '-startup.json')).write_text(json.dumps(snapshot, indent=2), encoding='utf-8')
                row.update(native_read=bool(windows), pid=process.pid, windows=windows,
                           node_count=len(nodes), roles=dict(Counter(n['role'] for n in nodes)),
                           startup_controls=[{'role': n['role'], 'name': n['name'], 'actions': n['actions']}
                                             for n in nodes if n['role'] in {'button', 'text_field', 'check_box'}])
                if not windows:
                    row['error'] = 'No native startup window was exposed'
        except Exception as error:
            row['error'] = str(error)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        rows.append(row)
        (output / 'summary.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
        print(json.dumps(row), flush=True)
    (output / 'inventory.done').write_text('done', encoding='utf-8')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apps', nargs='+', choices=APPS)
    parser.add_argument('--startup-wait', type=float, default=5)
    args = parser.parse_args()
    if not 0 <= args.startup_wait <= 60:
        parser.error('--startup-wait must be between 0 and 60 seconds')
    rows = inventory(args.apps or APPS, args.output, args.startup_wait)
    raise SystemExit(0 if all(row['native_read'] for row in rows) else 1)
