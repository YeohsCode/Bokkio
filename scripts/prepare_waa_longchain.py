"""Export three fixed WAA tasks, hash their assets and extract reviewed metrics."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import ssl
import subprocess
import urllib.request

import certifi


REVISION = '6d39ed88c545a0d40a7a02e39b928e278df7332b'
BASE = 'src/win-arena-container/client/'
SELECTED = [
    ('png-list', 'file_explorer/016c9a9d-f2b9-4428-8fdb-f74f4439ece6-WOS.json'),
    ('size-report', 'file_explorer/2d292a2d-686b-4e72-80f7-af6c232b1258-WOS.json'),
    ('word-count', 'notepad/a7d4b6c5-569b-452e-9e1d-ffdb3d431d15-WOS.json'),
]
METRICS = [
    ('desktop_env/evaluators/metrics/general.py', ['exact_match']),
    ('desktop_env/evaluators/metrics/vscode.py', ['compare_text_file']),
    ('desktop_env/evaluators/getters/fileexplorer.py', ['get_all_png_file_names', 'get_is_file_saved_desktop']),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def download(url, limit):
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, context=context, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError('Benchmark asset exceeds size limit')
    return data


def prepare(repo, output):
    output.mkdir(parents=True, exist_ok=False)
    def git(path):
        return subprocess.check_output(['git', '-C', str(repo), 'show', REVISION + ':' + path])
    manifest = {'benchmark': 'WindowsAgentArena', 'revision': REVISION,
                'selection_status': 'fixed_before_execution', 'scope': 'adapted_development_run',
                'tasks': [], 'metric_sources': []}
    for name, path in SELECTED:
        full = BASE + 'evaluation_examples_windows/examples/' + path
        raw = git(full)
        task = json.loads(raw)
        folder = output / name
        folder.mkdir()
        (folder / 'original.json').write_bytes(raw)
        assets = []
        for entry in task['config']:
            if entry['type'] != 'download':
                continue
            for asset in entry['parameters']['files']:
                namepart = asset['path'].split('\\')[-1]
                if namepart in {'.', '..', ''} or Path(namepart).name != namepart:
                    raise RuntimeError('Unexpected asset filename')
                dest = folder / 'inputs' / namepart
                dest.parent.mkdir(exist_ok=True)
                data = download(asset['url'], 32 * 1024 * 1024)
                dest.write_bytes(data)
                assets.append({'kind': 'input', 'url': asset['url'], 'file': 'inputs/' + namepart,
                               'sha256': sha(data), 'bytes': len(data)})
        expected = task['evaluator'].get('expected')
        if isinstance(expected, dict) and expected.get('type') == 'cloud_file':
            data = download(expected['path'], 4096)
            (folder / 'gold.txt').write_bytes(data)
            assets.append({'kind': 'gold', 'url': expected['path'], 'file': 'gold.txt',
                           'sha256': sha(data), 'bytes': len(data)})
        manifest['tasks'].append({'case': name, 'path': full, 'sha256': sha(raw),
                                  'id': task['id'], 'assets': assets, 'execution_status': 'not_run'})
    source = 'import logging, re\nlogger=logging.getLogger("waa.adapted")\n'
    for path, names in METRICS:
        raw = git(BASE + path)
        text = raw.decode()
        funcs = {n.name: n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
        for name in names:
            source += '\n' + ast.get_source_segment(text, funcs[name]) + '\n'
        manifest['metric_sources'].append({'path': BASE + path, 'sha256': sha(raw), 'functions': names})
    exported = source.encode('utf-8')
    (output / 'upstream_metrics.py').write_bytes(exported)
    manifest['metric_export_sha256'] = sha(exported)
    (output / 'LICENSE-WAA.txt').write_bytes(git('LICENSE'))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.checkout, args.output)
    print(json.dumps({'tasks': [t['case'] for t in result['tasks']], 'output': str(args.output)}))
