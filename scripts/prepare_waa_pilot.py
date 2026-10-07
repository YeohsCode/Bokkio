"""Export the preselected five WAA tasks and reviewed upstream evaluator code."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import textwrap

from prepare_waa_longchain import BASE, REVISION, download


EXPORTS = {
    'desktop_env/evaluators/metrics/general.py': ['exact_match'],
    'desktop_env/evaluators/metrics/vscode.py': ['compare_text_file'],
    'desktop_env/evaluators/getters/file.py': ['get_vm_file', 'get_cloud_file', 'get_vm_file_exists_in_vm_folder'],
    'desktop_env/evaluators/getters/fileexplorer.py': ['get_is_details_view', 'get_vm_active_window_title'],
    'desktop_env/evaluators/getters/settings.py': ['get_system_notifications'],
    'desktop_env/evaluators/getters/misc.py': ['get_rule'],
    'desktop_env/envs/desktop_env.py': ['evaluate'],
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare(checkout, output):
    selection = json.loads((Path(__file__).resolve().parents[1]/'docs/benchmarks/windows-arena-pilot.json').read_text())
    if selection['revision'] != REVISION or len(selection['tasks']) != 5:
        raise ValueError('Pilot selection changed')
    def read(path):
        return subprocess.check_output(['git', '-C', str(checkout), 'show', REVISION+':'+path])
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'benchmark':'WindowsAgentArena', 'revision':REVISION,
                'scope':'adapted_development_run', 'tasks':[], 'sources':[]}
    source = ('from __future__ import annotations\nimport os, re, logging\n'
              'from datetime import datetime\nfrom typing import *\n'
              'logger=logging.getLogger("waa.pilot")\n')
    for path, names in EXPORTS.items():
        raw = read(BASE+path)
        text = raw.decode('utf-8')
        functions = {n.name:n for n in ast.walk(ast.parse(text)) if isinstance(n,ast.FunctionDef)}
        for name in names:
            source += '\n'+textwrap.dedent(ast.get_source_segment(text, functions[name]))+'\n'
        manifest['sources'].append({'path':BASE+path, 'sha256':digest(raw), 'functions':names})
    exported = source.encode('utf-8')
    manifest['evaluator_sha256'] = digest(exported)
    (output/'upstream_evaluator.py').write_bytes(exported)
    for index, entry in enumerate(selection['tasks'],1):
        raw=read(entry['path']); task=json.loads(raw)
        folder=output/str(index); folder.mkdir()
        (folder/'original.json').write_bytes(raw)
        assets=[]
        for setup in task.get('config',[]):
            if setup['type']=='download':
                for asset in setup['parameters']['files']:
                    data=download(asset['url'], 1024*1024)
                    filename='input-'+str(len(assets))+'.bin'
                    (folder/filename).write_bytes(data)
                    assets.append({'kind':'input','url':asset['url'],'original_path':asset['path'],
                                   'file':filename,'sha256':digest(data)})
        expected=task['evaluator'].get('expected',[])
        for item in expected if isinstance(expected,list) else [expected]:
            if item and item['type']=='cloud_file':
                data=download(item['path'], 1024*1024)
                (folder/item['dest']).write_bytes(data)
                assets.append({'kind':'gold','url':item['path'],'file':item['dest'],'sha256':digest(data)})
        manifest['tasks'].append({'index':index,'path':entry['path'],'sha256':digest(raw),'assets':assets})
    (output/'LICENSE-WAA.txt').write_bytes(read('LICENSE'))
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=prepare(args.checkout,args.output)
    print(json.dumps({'tasks':len(result['tasks']), 'evaluator_sha256':result['evaluator_sha256']}))
