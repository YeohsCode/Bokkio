"""Run pinned WAA native long tasks in isolated folders; preserve all attempts.

Uses real Planner/Jev/UIA. Setup may create inputs and launch applications.
Only the agent writes deliverables; independently run the pinned metrics and
reopen artifacts in a fresh Notepad process. These are adapted development runs.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
import platform
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
from uuid import uuid4

from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend
from waa_variations import VARIANTS, prepare_variant, evaluate_variant


CASES = ['png-list', 'size-report', 'word-count']
# Hash of the reviewed AST export at the pinned revision. Never import a
# changed evaluator module merely because the bundle manifest says it is safe.
METRICS_SHA256 = '1132f467ffb3129f677f3d5565fbdcbb9419849b9c3542660d32315563c9d42d'


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def native_windows():
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    found = []
    def visit(hwnd, _):
        text = ctypes.create_unicode_buffer(user.GetWindowTextLengthW(hwnd) + 1)
        user.GetWindowTextW(hwnd, text, len(text))
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        found.append({'hwnd': int(hwnd), 'pid': pid.value, 'title': text.value})
        return True
    user.EnumWindows(callback_type(visit), 0)
    return found


class ScopedBackend:
    """Keep Explorer observations and actions on the window created for this task."""
    def __init__(self, backend, explorer=None):
        self.backend, self.explorer = backend, explorer
    def scope(self, app, window=None):
        if self.explorer and app == str(self.explorer['pid']):
            return f"hwnd:0x{self.explorer['hwnd']:x}"
        return window
    def snapshot(self, app, window=None):
        return self.backend.snapshot(app, self.scope(app, window))
    def windows(self, app):
        if not self.explorer or app != str(self.explorer['pid']):
            return self.backend.windows(app)
        snap = self.snapshot(app)
        return [{'name': n['name'], 'ref': n['ref']} for n in snap['windows']]
    def perform(self, app, action, **kwargs):
        kwargs['window'] = self.scope(app, kwargs.get('window'))
        return self.backend.perform(app, action, **kwargs)


class PauseAfterEditorWrite(ScopedBackend):
    """Pause through the public control hook after a real editor write."""
    def __init__(self, backend, explorer=None):
        super().__init__(backend, explorer)
        self.writes = 0
    def perform(self, app, action, **kwargs):
        result = super().perform(app, action, **kwargs)
        if action in {'set_value', 'type'} and result['before'].get('role') == 'text_area':
            self.writes += 1
        return result


def initialize_hidden_extensions(scoped, app):
    """Native fixture setup, separate from planner actions and deliverables."""
    from bokkio.model import tree_digest
    records=[]
    def node(role, name):
        snapshot=scoped.snapshot(app)
        matches=[n for n in flatten(snapshot['windows']) if n['role']==role and n['name']==name]
        if len(matches)!=1: raise RuntimeError('Setup needs one native '+name)
        return snapshot, matches[0]
    def act(role, name, action):
        snapshot,target=node(role,name)
        result=scoped.perform(app,action,ref=target['ref'],expected_snapshot=tree_digest(snapshot['windows']))
        records.append(result)
    _,view=node('button','View')
    if not view['state']['expanded']: act('button','View','expand')
    _,show=node('menu_item','Show')
    if not show['state']['expanded']: act('menu_item','Show','expand')
    _,setting=node('menu_item','File name extensions')
    checked=setting['state']['checked']
    if checked not in {True,False,'on','off'}:
        raise RuntimeError('Native extension toggle state is unavailable')
    if checked is True or checked=='on':
        act('menu_item','File name extensions','click')
        _,show=node('menu_item','Show')
        if not show['state']['expanded']: act('menu_item','Show','expand')
    _,setting=node('menu_item','File name extensions')
    if setting['state']['checked'] not in {False,'off'}:
        raise RuntimeError('Native extension toggle did not become unchecked')
    act('button','View','collapse')
    return {'purpose':'native input fixture setup only', 'hidden_extensions_verified':True, 'actions':records}


class ReadonlyController:
    """Transport for the reviewed upstream getters, used only after execution."""
    def __init__(self, desktop): self.desktop = desktop
    def get_vm_desktop_path(self): return str(self.desktop)
    def get_file_as_text(self, path):
        p = Path(path)
        return p.read_text(encoding='utf-8-sig') if p.is_file() else None
    def execute_python_command(self, script):
        # Only the vendored get_all_png_file_names calls this adapter. Its source
        # is pinned and reviewed; model text never becomes executable code.
        result = subprocess.run([sys.executable, '-c', script], capture_output=True,
                                text=True, timeout=10)
        return {'status': 'success' if result.returncode == 0 else 'error',
                'output': result.stdout, 'error': result.stderr}


def load_metrics(bundle):
    if hashlib.sha256((bundle / 'upstream_metrics.py').read_bytes()).hexdigest() != METRICS_SHA256:
        raise RuntimeError('Reviewed evaluator export hash changed')
    spec = importlib.util.spec_from_file_location('waa_pinned_metrics', bundle / 'upstream_metrics.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapted_goal(instruction, folders, inputs, artifact):
    # Substitute the same isolated bindings directly where the source task
    # mentions them, so a pinned personal folder is not mistaken for test data.
    adapted = instruction
    for name, path in folders.items():
        adapted = re.sub(r'\b' + re.escape(name) + r' folder\b',
                         lambda _: f'folder "{path}"', adapted, flags=re.I)
    for path in inputs:
        adapted = adapted.replace(f'"{path.name}"', f'"{path}"')
    bindings = '; '.join(f'{k} means "{v}"' for k,v in folders.items())
    adapted += '\nIsolated task folder bindings: ' + bindings + '. '
    adapted += f'Use Notepad for the output and save the deliverable at "{artifact}". '
    adapted += 'Use full isolated paths in file dialogs; pinned personal folders are outside this task. '
    adapted += 'All input documents and these folders belong to this disposable test. Do not use scripts or shell commands.'
    return adapted


def checks_from_trace(trace, source, artifact, case, inputs, *, require_full_names=False):
    snaps = []
    for event in trace.get('events', []):
        if event.get('kind') in {'observation', 'outcome'}:
            snaps.append(flatten(event['snapshot']['windows']))
        elif event.get('kind') == 'planner_observations':
            for observation in event['observations'].values():
                snaps.append(observation['nodes'])
    if case == 'word-count':
        content = (source / 'largefile.txt').read_text(encoding='utf-8')
        source_seen = any(any(n.get('role') == 'text_area' and
                              n.get('value', '').replace('\r\n', '\n') == content.replace('\r\n', '\n')
                              for n in nodes if isinstance(n.get('value'), str)) for nodes in snaps)
    else:
        # Input filenames are setup metadata, never hidden evaluator answers.
        # Explorer may hide just the final suffix (ignore.png.txt -> ignore.png).
        # Never strip a second suffix from the displayed native name.
        source_seen = any(all(any(n.get('role') == 'list_item' and
                                  n.get('name') in ({p.name} if require_full_names else {p.name,p.stem}) for n in nodes)
                              for p in inputs) for nodes in snaps)
    actions = [e for e in trace.get('events', []) if e.get('kind') == 'action']
    save_actions = [e for e in actions if e['result']['before'].get('name') == 'Save'
                    and e['result']['before'].get('role') == 'button'
                    and e['result']['action'] in {'click', 'invoke'}]
    native_text = False
    if artifact.is_file():
        content = artifact.read_text(encoding='utf-8-sig')
        native_text = any(any(n.get('role') == 'text_area' and isinstance(n.get('value'), str)
                             and n['value'].replace('\r\n', '\n') == content.replace('\r\n', '\n')
                             for n in nodes) for nodes in snaps)
    return {'source_observed_natively': source_seen,
            'text_observed_natively': native_text,
            'save_dialog_observed': any(any(n.get('role') == 'dialog' and n.get('name') == 'Save As'
                                           for n in nodes) for nodes in snaps),
            'save_target_observed': any(any(n.get('role') == 'text_field' and
                                           n.get('value') == str(artifact) for n in nodes) for nodes in snaps),
            'native_save_dispatched': bool(save_actions)}


def run(bundle, output, cases, rounds=1, variants=None, pause_before_save=False, hidden_extensions=False):
    import xa11y
    if output.exists(): raise RuntimeError('Use a new output directory for independent initial state')
    output.mkdir(parents=True)
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if manifest['revision'] != '6d39ed88c545a0d40a7a02e39b928e278df7332b':
        raise RuntimeError('Unexpected WAA revision')
    for task in manifest['tasks']:
        folder = bundle / task['case']
        if hashlib.sha256((folder / 'original.json').read_bytes()).hexdigest() != task['sha256']:
            raise RuntimeError('Task hash changed')
        for asset in task['assets']:
            if hashlib.sha256((folder / asset['file']).read_bytes()).hexdigest() != asset['sha256']:
                raise RuntimeError('Input or gold asset hash changed')
    metrics = load_metrics(bundle)
    planner = OpenRouterPlanner(reasoning_effort='low')
    rows = []
    selected = ([dict(next(t for t in manifest['tasks'] if t['case'] == VARIANTS[v]), variant=v)
                 for v in variants] if variants else [t for t in manifest['tasks'] if t['case'] in cases])
    source_hashes = {name: hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()
                     for name in ['bokkio.agent', 'bokkio.planner', 'bokkio.decision', 'bokkio.xa11y_backend', 'bokkio.jev', 'bokkio.windows_uia']}
    harness_hashes = {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                      for name in ['verify_waa_longchain.py','waa_variations.py']}
    save(output / 'selection.json', {'manifest':manifest, 'cases':cases, 'variants':variants,
                                    'pause_before_save':pause_before_save, 'rounds':rounds,
                                    'hidden_extensions_setup':hidden_extensions,
                                    'max_actions':32, 'max_replans':2, 'max_phases':8, 'planner_model':planner.model, 'planner_reasoning_effort':'low',
                                    'python':sys.version, 'platform':platform.platform(), 'source_hashes':source_hashes,
                                    'harness_hashes':harness_hashes,
                                    'selected_before_execution':True})
    scope = 'WAA_derived_robustness_fixtures' if variants else 'adapted_WAA_development_run'
    summary = {'scope':scope,'planned':len(selected)*rounds,
               'attempted':0,'passed':0,'results':rows}
    save(output / 'summary.json', summary)
    for iteration in range(1, rounds + 1):
        for task in selected:
            backend = Xa11yBackend()  # Each case binds fresh process identities.
            case = task['case']; variant = task.get('variant')
            directory = output / f'{variant or case}-r{iteration}'
            directory.mkdir()
            world = directory / ('world-' + uuid4().hex[:8]); world.mkdir()
            folders = {k:world / k for k in ['Pictures','Downloads','Desktop','Documents']}
            for p in folders.values(): p.mkdir()
            original = json.loads((bundle / case / 'original.json').read_text())
            source = folders['Pictures' if case == 'png-list' else 'Downloads' if case == 'size-report' else 'Documents']
            inputs = []
            expected = None
            if variant:
                inputs, instruction, expected = prepare_variant(variant, source)
            else:
                instruction = original['instruction']
                for asset in task['assets']:
                    if asset['kind'] == 'input':
                        dest = source / Path(asset['file']).name
                        shutil.copyfile(bundle / case / asset['file'], dest); inputs.append(dest)
            if case == 'size-report' and not variant:
                # Reviewed equivalent of upstream fsutil createnew; setup only.
                with (source / 'testing.bin').open('wb') as file: file.truncate(15000000)
                inputs.append(source / 'testing.bin')
            artifact = (folders['Pictures'] / 'png_files.txt' if case == 'png-list' else
                        folders['Desktop'] / 'report.txt' if case == 'size-report' else
                        folders['Documents'] / 'example_count.txt')
            owned, explorer = [], None
            started = time.perf_counter()
            row = {'case':case,'variant':variant,'round':iteration,'task_path':task['path'],'task_sha256':task['sha256'],
                   'scope':scope,'passed':False}
            trace = {}
            input_hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
            save(directory / 'setup.json', {'folders':{k:str(v) for k,v in folders.items()},
                                            'artifact':str(artifact), 'inputs':[
                                                {'name':p.name,'bytes':p.stat().st_size,'sha256':input_hashes[p]} for p in inputs]})
            if variant:
                save(directory/'oracle.json', {'expected':expected, 'execution_feedback':False})
            try:
                note = subprocess.Popen(['notepad.exe']); owned.append(note)
                xa11y.App.by_pid(note.pid, timeout=30)
                time.sleep(0.5)
                apps = [str(note.pid)]
                if case != 'word-count':
                    existing = {w['hwnd'] for w in native_windows()}
                    subprocess.Popen(['explorer.exe',str(source)])
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        matches = [w for w in native_windows() if w['hwnd'] not in existing
                                   and w['title'] in {source.name,source.name+' - File Explorer'}]
                        if len(matches) == 1:
                            explorer = matches[0]; break
                        time.sleep(0.2)
                    if explorer is None: raise RuntimeError('Unique owned Explorer window did not appear')
                    xa11y.App.by_pid(explorer['pid'], timeout=20)
                    apps.insert(0,str(explorer['pid']))
                scoped = (PauseAfterEditorWrite(backend, explorer) if pause_before_save
                          else ScopedBackend(backend, explorer))
                if hidden_extensions and case=='png-list':
                    save(directory/'preflight.json',initialize_hidden_extensions(scoped,str(explorer['pid'])))
                initial = {app:scoped.snapshot(app) for app in apps}
                save(directory / 'initial.json',initial)
                goal = adapted_goal(instruction, folders, inputs, artifact)
                save(directory / 'goal.json',{'original_instruction':original['instruction'],'adapted_goal':goal})
                # This feedback exposes only the requested file's existence;
                # no gold values or metric answers enter the execution loop.
                def delivery(trace):
                    exists = artifact.is_file()
                    return exists, {'required_artifact':str(artifact), 'exists':exists}
                required_sources=[str(source/'largefile.txt')] if case=='word-count' else []
                control = (lambda: 'pause' if scoped.writes else None) if pause_before_save else None
                trace = DesktopAgent(scoped,planner,JevProvider(),max_actions=32,max_replans=2,max_phases=8,
                                     control=control,final_verifier=delivery,required_sources=required_sources).run(
                    goal,apps,directory/'trace.json')
                resume_checks = {}
                if pause_before_save:
                    save(directory/'paused.json', trace)
                    prefix = list(trace['events'])
                    actions_before = trace['actions']
                    resume_checks = {'paused_after_editor_write':trace['status']=='paused' and scoped.writes==1,
                                     'paused_before_persistence':not artifact.exists()}
                    if trace['status']=='paused':
                        resumed_backend = PauseAfterEditorWrite(Xa11yBackend(), explorer)
                        trace = DesktopAgent(resumed_backend,planner,JevProvider(),max_actions=32,max_replans=2,
                                             max_phases=8,final_verifier=delivery,required_sources=required_sources).run(
                            goal,apps,directory/'trace.json',resume=directory/'paused.json')
                        resume_checks.update(checkpoint_history_preserved=trace['events'][:len(prefix)]==prefix,
                                             editor_write_not_repeated=resumed_backend.writes==0,
                                             save_actions_after_resume=trace['actions']>actions_before)
                        backend = resumed_backend.backend
                mid = checks_from_trace(trace,source,artifact,case,inputs,
                                        require_full_names=bool(variant and case=='png-list'))
                env = SimpleNamespace(controller=ReadonlyController(folders['Desktop']))
                if variant:
                    score = None  # Original gold/metrics do not score custom inputs.
                    result = None
                    oracle_passed = evaluate_variant(case, artifact, expected)
                elif case == 'png-list':
                    result = metrics.get_all_png_file_names(env,{'folder_path':str(source),'file_path':str(artifact)})
                    score = metrics.exact_match(result,original['evaluator']['expected']['rules'])
                elif case == 'size-report':
                    result = metrics.get_is_file_saved_desktop(env,original['evaluator']['result'])
                    score = metrics.exact_match(result,original['evaluator']['expected']['rules'])
                else:
                    score = metrics.compare_text_file(str(artifact) if artifact.exists() else None,str(bundle/case/'gold.txt'))
                    result = None
                if not variant:
                    oracle_passed = score == 1.0
                extra = {'persisted_artifact_exists':artifact.is_file(),
                         'input_bytes_preserved':all(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest
                                                     for p,digest in input_hashes.items())}
                if case == 'size-report' and artifact.is_file():
                    actual = set(artifact.read_text(encoding='utf-8-sig').splitlines())
                    expected = {p.name for p in inputs if p.stat().st_size > 5*1024*1024}
                    extra['exact_large_file_names'] = actual == expected
                reopened = False
                if artifact.is_file():
                    before = artifact.read_bytes()
                    # Independent verification setup: reopen saved output in a
                    # fresh process. This is recorded separately from agent actions.
                    reopened_note = subprocess.Popen(['notepad.exe',str(artifact)]);owned.append(reopened_note)
                    xa11y.App.by_pid(reopened_note.pid,timeout=20);time.sleep(0.5)
                    snap = backend.snapshot(str(reopened_note.pid));save(directory/'reopened.json',snap)
                    expected_text = artifact.read_text(encoding='utf-8-sig')
                    reopened = any(n['role']=='text_area' and isinstance(n['value'],str)
                                   and n['value'].replace('\r\n','\n')==expected_text.replace('\r\n','\n')
                                   for n in flatten(snap['windows']))
                    extra['reopen_kept_bytes'] = artifact.read_bytes() == before
                    row['artifact_sha256'] = hashlib.sha256(before).hexdigest()
                extra['fresh_process_native_reopen'] = reopened
                row.update(agent_status=trace['status'],actions=trace['actions'],replans=trace['replans'],
                           phases=trace.get('phases',0),
                           completed_steps=trace['completed_steps'],intermediate_checks=mid,
                           final_checks=extra,resume_checks=resume_checks, independent_oracle_passed=oracle_passed,
                           pinned_metric_score=score,pinned_getter_result=result,
                           passed=trace['status']=='completed' and oracle_passed and all(mid.values())
                                  and all(extra.values()) and all(resume_checks.values()))
            except Exception as error:
                row.update(error=str(error),agent_status=trace.get('status'),actions=trace.get('actions',0),
                           replans=trace.get('replans',0))
            finally:
                for process in owned:
                    if process.poll() is None:
                        process.terminate();process.wait(timeout=10)
                if explorer:
                    # Close only the HWND this verifier created, never the shell process.
                    user=ctypes.WinDLL('user32',use_last_error=True)
                    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
                    if any(w['hwnd']==explorer['hwnd'] and w['pid']==explorer['pid'] for w in native_windows()):
                        user.PostMessageW(explorer['hwnd'],0x0010,0,0)
                row['seconds']=round(time.perf_counter()-started,3)
                save(directory/'result.json',row);rows.append(row)
                summary.update(attempted=len(rows),passed=sum(r['passed'] for r in rows))
                save(output/'summary.json',summary)
                print(json.dumps(row),flush=True)
    (output/'done').write_text('done',encoding='utf-8')
    return summary['passed']==summary['planned']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cases',nargs='+',choices=CASES,default=CASES)
    parser.add_argument('--rounds',type=int,default=1)
    parser.add_argument('--variants',nargs='+',choices=list(VARIANTS))
    parser.add_argument('--pause-before-save',action='store_true')
    parser.add_argument('--hidden-extensions',action='store_true',help='Initialize PNG fixtures with extensions hidden using native UIA')
    args=parser.parse_args()
    if len(set(args.cases))!=len(args.cases) or not 1<=args.rounds<=3:parser.error('Use unique cases and 1–3 rounds')
    if args.variants and len(set(args.variants))!=len(args.variants):parser.error('Use unique variants')
    raise SystemExit(0 if run(args.bundle,args.output,args.cases,args.rounds,args.variants,args.pause_before_save,args.hidden_extensions) else 1)
