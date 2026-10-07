"""Run the fixed five WAA pilots with per-action native dispatch and pinned scoring.

The Fusion ARM64 environment and local controller are documented adaptations.
Setup/evaluation commands never enter Planner/Jev's action space.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import faulthandler
import shutil
import subprocess
import time
from types import SimpleNamespace

from bokkio.agent import DesktopAgent
from bokkio.arena import NativeArenaAgent, WAAAgentAdapter
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend
from verify_waa_longchain import ScopedBackend, native_windows, save


# Filled from the reviewed, deterministic AST export at the pinned revision.
EVALUATOR_SHA256 = 'c340c602905fda043021421dac28023c246dae64398df8200d9dd2f056f152fa'
MANIFEST_SHA256 = '2c22f00e2b208cb5c019a6c1e019746efce640932c0054021f1ac965afbd76de'
BUDGETS = {'max_actions':24,'max_replans':3,'max_phases':8}
NOTIFICATION_KEY = r'Software\Microsoft\Windows\CurrentVersion\PushNotifications'


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wait_ready_window(title, timeout=30, discover=None, resolve=None):
    """A Win32 caption can precede UIA registration or belong to a closing host."""
    if discover is None:
        user=ctypes.WinDLL('user32')
        user.IsWindowVisible.argtypes=[wintypes.HWND]
        user.IsWindowVisible.restype=wintypes.BOOL
        def discover():
            return [w for w in native_windows() if user.IsWindowVisible(w['hwnd'])]
    if resolve is None:
        import xa11y
        resolve=xa11y.App.by_pid
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        matches=[w for w in discover() if w['title']==title]
        ready=[]
        for candidate in matches:
            try:
                resolve(candidate['pid'],timeout=0)
                ready.append(candidate)
            except Exception:
                pass
        if len(ready)==1:
            candidate=ready[0]
            # Settings also exposes an unregistered hidden CoreWindow with the
            # same caption. Bind only the unique visible, registered app root.
            if any(w['hwnd']==candidate['hwnd'] and w['pid']==candidate['pid']
                   and w['title']==title for w in discover()):
                return candidate
        time.sleep(0.2)
    raise RuntimeError(f'{title} did not expose one live UIA application within the startup deadline')


class Timed:
    def __init__(self, target, lane, records):
        self.target,self.lane,self.records=target,lane,records
    def __getattr__(self, name):
        value=getattr(self.target,name)
        if name not in {'plan','ask','snapshot','windows','perform'}:return value
        def call(*args,**kwargs):
            started=time.monotonic()
            try:return value(*args,**kwargs)
            finally:self.records.append({'lane':self.lane,'method':name,
                                         'seconds':time.monotonic()-started})
        return call


def shell_view(folder, set_mode=None):
    """Harness-only Shell COM read/setup; native actor cannot call this function."""
    script = ('$s=New-Object -ComObject Shell.Application; '
              '$w=@($s.Windows() | Where-Object { '
              'try {$_.Document.Folder.Self.Path -eq $env:BOKKIO_EVAL_FOLDER} catch {$false} }); '
              'if ($w.Count -ne 1) {throw "Need one owned folder view"}; ')
    if set_mode is not None:
        script += f'$w[0].Document.CurrentViewMode={int(set_mode)}; '
    script += '$w[0].Document.CurrentViewMode'
    environment = {**os.environ, 'BOKKIO_EVAL_FOLDER': str(folder)}
    result = subprocess.run(['powershell.exe','-NoProfile','-Command',script],
                            env=environment,capture_output=True,text=True,timeout=20,check=True)
    return int(result.stdout.strip())


def shell_folder_path(explorer):
    """Independent business-state read scoped to the harness-owned Explorer HWND."""
    script = ('$s=New-Object -ComObject Shell.Application; '
              '$w=@($s.Windows() | Where-Object { '
              'try {[Int64]$_.HWND -eq [Int64]$env:BOKKIO_EVAL_HWND} catch {$false} }); '
              'if ($w.Count -ne 1) {throw "Need one owned Explorer window"}; '
              '$w[0].Document.Folder.Self.Path')
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],
                          env={**os.environ,'BOKKIO_EVAL_HWND':str(explorer['hwnd'])},
                          capture_output=True,text=True,timeout=20,check=True)
    return result.stdout.strip()


def notification_native_fixture(app, desired):
    """Harness setup/restoration through native navigation and the real toggle."""
    backend=Xa11yBackend();navigation=[];routes=set();focused=False
    deadline=time.monotonic()+25
    while True:
        try:
            snapshot=backend.snapshot(app)
            nodes=flatten(snapshot['windows'])
        except Exception:
            nodes=[]
        toggles=[n for n in nodes if n['role']=='button' and n['name']=='Notifications'
                 and type(n['state'].get('checked')) is bool]
        if len(toggles)==1:break
        # Settings can expose only its frame until it receives native focus.
        frames=[n for n in nodes if n['role']=='window' and n['name']=='Settings'
                and 'focus' in n['actions']]
        if not focused and len(frames)==1:
            navigation.append(backend.perform(app,'focus',ref=frames[0]['ref']))
            focused=True
            time.sleep(0.2)
            continue
        rows=[n for n in nodes if n['role']=='list_item' and n['name']=='Notifications'
              and 'click' in n['actions']]
        systems=[n for n in nodes if n['role']=='list_item' and n['name']=='System'
                 and 'click' in n['actions']]
        target=None
        if len(rows)==1 and 'notifications' not in routes:
            target=rows[0];routes.add('notifications')
        elif len(systems)==1 and not routes:
            target=systems[0];routes.add('system')
        if target is not None:
            navigation.append(backend.perform(app,'click',ref=target['ref']))
        if time.monotonic()>=deadline:
            raise RuntimeError('Native Notifications page did not expose one toggle within the setup deadline')
        time.sleep(0.2)
    before=toggles[0]['state']['checked'];receipt=None
    if before!=desired:
        receipt=backend.perform(app,'click',ref=toggles[0]['ref'])
        fresh=backend.snapshot(app)
        observed=[n['state']['checked'] for n in flatten(fresh['windows']) if n['role']=='button'
                  and n['name']=='Notifications' and type(n['state'].get('checked')) is bool]
        if observed!=[desired]:raise RuntimeError('Native notification fixture did not reach its required state')
    return {'before':before,'desired':desired,'navigation':navigation,'receipt':receipt}


class Controller:
    def __init__(self, root, explorer):
        self.root, self.explorer, self.reads = root, explorer, []

    def get_file(self, path):
        p=Path(path).resolve()
        if not p.is_relative_to(self.root.resolve()):
            raise ValueError('Evaluator read outside isolated task')
        return p.read_bytes() if p.is_file() else None

    def execute_python_command(self, script):
        if script != 'import pyautogui; print(pyautogui.getActiveWindowTitle())':
            raise ValueError('Unreviewed evaluator command')
        user=ctypes.WinDLL('user32')
        user.GetForegroundWindow.restype=wintypes.HWND
        hwnd=user.GetForegroundWindow()
        title=ctypes.create_unicode_buffer(4096)
        user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
        user.GetWindowTextW(hwnd,title,len(title))
        self.reads.append({'getter':'active_window_title','transport':'Win32 GetForegroundWindow/GetWindowTextW','value':title.value})
        return {'status':'success','output':title.value+'\n','error':''}

    def get_vm_file_explorer_is_details_view(self, path):
        if Path(path).resolve()!= (self.root/'Documents').resolve():
            raise ValueError('Unexpected folder')
        mode=shell_view(path)
        self.reads.append({'getter':'details_view','transport':'Shell COM CurrentViewMode','value':mode})
        return mode==4

    def get_registry_key(self, key, setting):
        import winreg
        if key!=r'HKCU:'+NOTIFICATION_KEY or setting!='ToastEnabled':
            raise ValueError('Unexpected registry getter')
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,NOTIFICATION_KEY) as handle:
                value,_=winreg.QueryValueEx(handle,'ToastEnabled')
        except FileNotFoundError:
            value=None
        self.reads.append({'getter':'system_notifications','value':value})
        return {'output':'' if value is None else str(value)+'\n'}


class Setup:
    def __init__(self, owned, explorer, output):
        self.owned,self.explorer,self.output,self.records=owned,explorer,output,[]
        self.preferred_pid=None

    def setup(self, entries):
        for entry in entries:
            kind,p=entry['type'],entry['parameters']
            record={'entry':entry,'phase':'official_evaluator_postconfig'}
            if kind=='sleep':
                time.sleep(min(float(p['seconds']),2))
            elif kind=='open':
                if not Path(p['path']).is_file():
                    raise FileNotFoundError('Evaluator postconfig artifact does not exist')
                process=subprocess.Popen(['notepad.exe',p['path']]);self.owned.append(process)
                self.preferred_pid=process.pid
                import xa11y
                xa11y.App.by_pid(process.pid,timeout=20)
                time.sleep(0.5)
                save(self.output/'reopened.json',Xa11yBackend().snapshot(str(process.pid)))
            elif kind=='activate_window':
                names={p['window_name']}
                if self.explorer:names.add(p['window_name']+' - File Explorer')
                candidates=[w for w in native_windows() if w['title'] in names
                            and (w['pid'] in {proc.pid for proc in self.owned}
                                 or self.explorer and w['hwnd']==self.explorer['hwnd'])]
                if self.preferred_pid is not None:
                    candidates=[w for w in candidates if w['pid']==self.preferred_pid]
                if len(candidates)!=1:
                    raise RuntimeError('Postconfig requires one owned matching window')
                user=ctypes.WinDLL('user32')
                user.SetForegroundWindow.argtypes=[wintypes.HWND]
                record['foreground_requested']=bool(user.SetForegroundWindow(candidates[0]['hwnd']))
            else:
                raise ValueError('Unreviewed postconfig type: '+kind)
            self.records.append(record)
        save(self.output/'postconfig.json',self.records)


def bind_paths(value, root):
    if isinstance(value,dict):return {k:bind_paths(v,root) for k,v in value.items()}
    if isinstance(value,list):return [bind_paths(v,root) for v in value]
    if isinstance(value,str):
        for name in ['Documents','Desktop']:
            for prefix in ['C:\\Users\\Docker\\'+name,'C:/Users/Docker/'+name]:
                if value==prefix or value.startswith(prefix+'\\') or value.startswith(prefix+'/'):
                    suffix=value[len(prefix):].strip('\\/').replace('\\','/')
                    return str(root/name/Path(suffix))
        return value
    return value


def load_evaluator(bundle):
    if hash_file(bundle/'upstream_evaluator.py')!=EVALUATOR_SHA256:
        raise ValueError('Reviewed evaluator export changed')
    spec=importlib.util.spec_from_file_location('waa_pilot_pinned',bundle/'upstream_evaluator.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def evaluate(module, config, controller, setup, cache, history):
    e=config['evaluator']
    funcs=e['func']; multi=isinstance(funcs,list)
    def getter(item):return getattr(module,'get_'+item['type']) if item else None
    env=SimpleNamespace(evaluator=e,controller=controller,setup_controller=setup,
                        cache_dir=str(cache),action_history=history,metric_conj=e.get('conj','and'))
    env.metric=[getattr(module,f) for f in funcs] if multi else getattr(module,funcs)
    env.result_getter=[getter(x) for x in e['result']] if multi else getter(e['result'])
    env.expected_getter=[getter(x) for x in e['expected']] if multi else getter(e.get('expected'))
    env.metric_options=e.get('options',[{} for _ in funcs] if multi else {})
    # Exact upstream DesktopEnv.evaluate body, including FAIL and conjunction semantics.
    return module.evaluate(env)


def run(bundle, output, selection=None):
    import winreg
    import xa11y
    module=load_evaluator(bundle)
    if hash_file(bundle/'manifest.json')!=MANIFEST_SHA256:
        raise ValueError('Pinned pilot manifest changed')
    manifest=json.loads((bundle/'manifest.json').read_text())
    if manifest['revision']!='6d39ed88c545a0d40a7a02e39b928e278df7332b' or len(manifest['tasks'])!=5:
        raise ValueError('Wrong fixed pilot bundle')
    output.mkdir(parents=True,exist_ok=False)
    selected=selection or [1,2,3,4,5]
    summary={'scope':'adapted_development_run','revision':manifest['revision'],'planned':len(selected),
             'budgets':dict(BUDGETS),
             'selection':selected,'attempted':0,'passed':0,'results':[],
             'environment':{'platform':platform.platform(),'machine':platform.machine(),
                            'python':platform.python_version()},
             'models':{'planner':os.environ.get('BOKKIO_PLANNER_MODEL','openai/gpt-4.1'),
                       'jev':JevProvider().model},
             'evaluator_sha256':EVALUATOR_SHA256,
             'source_sha256':{p.name:hash_file(p) for p in [Path(__file__),*[Path(__file__).parents[1]/'src/bokkio'/name
                for name in ['arena.py','agent.py','planner.py','decision.py','xa11y_backend.py','windows_uia.py']]]}}
    save(output/'summary.json',summary)
    for item in manifest['tasks']:
        index=item['index']
        if index not in selected:continue
        folder=output/str(index);folder.mkdir()
        root=folder/'task';root.mkdir()
        for name in ['Desktop','Documents','Start']: (root/name).mkdir()
        raw=bundle/str(index)/'original.json'
        if hash_file(raw)!=item['sha256']:raise ValueError('Task hash changed')
        original=json.loads(raw.read_text());config=bind_paths(original,root)
        save(folder/'original.json',original);save(folder/'adapted.json',config)
        cache=folder/'cache';cache.mkdir()
        for asset in item['assets']:
            source=bundle/str(index)/asset['file']
            if hash_file(source)!=asset['sha256']:raise ValueError('Asset hash changed')
            dest=Path(bind_paths(asset['original_path'],root)) if asset['kind']=='input' else cache/asset['file']
            shutil.copyfile(source,dest)
        owned=[];explorer=None;arena=None;notification_before=None;notification_fixture=False;owned_settings=None;timings=[];abort=False;input_hashes={};notification_native_setup=None
        row={'index':index,'task_path':item['path'],'task_sha256':item['sha256'],'passed':False,
             'scope':'adapted_development_run','native_steps':0,'metric_score':None}
        started=time.monotonic()
        try:
            if 'file_explorer' in config['related_apps']:
                start=root/('Start' if index==2 else 'Documents')
                existing={w['hwnd'] for w in native_windows()}
                subprocess.Popen(['explorer.exe',str(start)])
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    matches=[w for w in native_windows() if w['hwnd'] not in existing
                             and w['title'] in {start.name,start.name+' - File Explorer'}]
                    if len(matches)==1:explorer=matches[0];break
                    time.sleep(0.2)
                if not explorer:raise RuntimeError('Owned Explorer window did not appear')
                apps=[str(explorer['pid'])]
                xa11y.App.by_pid(explorer['pid'],timeout=20)
                if index==3:shell_view(start,1)
            elif 'notepad' in config['related_apps']:
                process=subprocess.Popen(['notepad.exe']);owned.append(process)
                xa11y.App.by_pid(process.pid,timeout=20);apps=[str(process.pid)]
            else:
                # Prepare notifications through the actual native toggle so
                # its original state is captured before any setting is changed.
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,NOTIFICATION_KEY) as key:
                    try:notification_before=winreg.QueryValueEx(key,'ToastEnabled')
                    except FileNotFoundError:pass
                    notification_fixture=True
                subprocess.run(['taskkill.exe','/IM','SystemSettings.exe','/F'],capture_output=True,timeout=10)
                existing={w['hwnd'] for w in native_windows()}
                subprocess.Popen(['cmd.exe','/c','start','','ms-settings:notifications'])
                settings=wait_ready_window('Settings')
                apps=[str(settings['pid'])]
                if settings['hwnd'] not in existing:owned_settings=settings
                notification_native_setup=notification_native_fixture(apps[0],True)
                backend=Xa11yBackend()
                home=[n for n in flatten(backend.snapshot(apps[0])['windows']) if n['role']=='list_item' and n['name']=='Home']
                if len(home)!=1:raise RuntimeError('Need one native Settings Home navigation item')
                notification_native_setup['return_home']=backend.perform(apps[0],'click',ref=home[0]['ref'])
            time.sleep(0.5)
            initial_backend=ScopedBackend(Xa11yBackend(),explorer)
            save(folder/'initial.json',{app:initial_backend.snapshot(app) for app in apps})
            save(folder/'setup.json',{'original_config':original['config'],'path_bindings':{
                r'C:\Users\Docker\Documents':str(root/'Documents'),r'C:\Users\Docker\Desktop':str(root/'Desktop')},
                'additional_fixture':'fresh owned app; disposable folders; Details starts in icons; notifications starts enabled',
                'settings_reset':'restart SystemSettings.exe; bind unique visible UIA-ready root; use native toggle only' if index==5 else None,
                'notifications_before':notification_before,
                'notifications_native_setup':notification_native_setup,
                'input_hashes':{str(p.relative_to(root)):hash_file(p) for p in root.rglob('*') if p.is_file()}})
            goal=original['instruction']
            if index in {1,2,4}:
                goal+=f'\nFor this disposable task, Documents means "{root/"Documents"}" and Desktop means "{root/"Desktop"}". Use these full paths in native address/file fields. '
            goal+='\nOperate through native controls. Do not use scripts, terminals or shell commands.'
            save(folder/'goal.json',{'instruction':goal})
            input_hashes={p:hash_file(p) for p in root.rglob('*') if p.is_file()}
            def factory(gated):
                return DesktopAgent(gated,Timed(OpenRouterPlanner(),'planner',timings),
                                    Timed(JevProvider(),'jev',timings),**BUDGETS)
            arena=NativeArenaAgent(lambda:Timed(ScopedBackend(Xa11yBackend(),explorer),'uia',timings),factory,apps,folder/'trace.json')
            adapter=WAAAgentAdapter(arena)
            history=[]
            for _ in range(28):
                _,predicted,_,_=adapter.predict(goal,{})
                if len(predicted)!=1:raise RuntimeError('Pilot requires one action per step')
                action=predicted[0]
                if isinstance(action,str):history.append(action);break
                receipt=arena.step(action);history.append(action)
                save(folder/'runner-steps.json',arena.steps)
                row['native_steps']=len(arena.steps)
            else:raise RuntimeError('Runner step limit exhausted')
            trace=arena.trace or {};row['agent_status']=trace.get('status')
            save(folder/'final-native.json',{app:initial_backend.snapshot(app) for app in apps})
            row['action_budget_used']=trace.get('actions');row['replans']=trace.get('replans')
            successful=sum(s['passed'] for s in arena.steps)
            action_events=sum(e['kind']=='action' for e in trace.get('events',[]))
            row['intermediate_checks']={'one_action_per_runner_step':len(history)==len(arena.steps)+1,
                'successful_dispatches_match_trace':successful==action_events,
                'native_observation_after_each_success':sum(e['kind']=='outcome' for e in trace.get('events',[]))==successful}
            controller=Controller(root,explorer);setup=Setup(owned,explorer,folder)
            if index==2:
                observed_folder=shell_folder_path(explorer)
                row['business_checks']={'getter':'Shell COM owned HWND folder path',
                    'observed_folder':observed_folder,'expected_folder':str(root/'Documents'),
                    'destination_folder_matches':Path(observed_folder).resolve()==(root/'Documents').resolve()}
            try:
                row['metric_score']=evaluate(module,config,controller,setup,cache,history)
            except FileNotFoundError as error:
                row['metric_score']=0.0
                row['evaluation_error']=str(error)
            save(folder/'evaluator-reads.json',controller.reads)
            artifacts={str(p.relative_to(root)):{'sha256':hash_file(p),'bytes':p.stat().st_size}
                       for p in root.rglob('*') if p.is_file()}
            row['artifacts']=artifacts
            row['input_bytes_preserved']=all(p.is_file() and hash_file(p)==h for p,h in input_hashes.items())
            row['passed']=row['metric_score']==1 and row['agent_status']=='completed' and all(row['intermediate_checks'].values()) and row['input_bytes_preserved']
        except Exception as error:
            row['error']=str(error)
        finally:
            if arena:
                row['native_steps']=len(arena.steps)
                save(folder/'runner-steps.json',arena.steps)
                try:arena.close()
                except Exception as error:
                    row['cleanup_error']=str(error)
                    abort=True
            for process in owned:
                if process.poll() is None:
                    process.terminate();process.wait(timeout=10)
            if explorer:
                user=ctypes.WinDLL('user32');user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
                user.PostMessageW(explorer['hwnd'],0x0010,0,0)
            if notification_native_setup is not None:
                try:
                    restored=notification_native_fixture(apps[0],notification_native_setup['before'])
                    save(folder/'notification-native-restored.json',restored)
                    row['notification_native_restored']=True
                except Exception as error:
                    row['notification_native_restored']=False;row['notification_restore_error']=str(error)
            if owned_settings:
                user=ctypes.WinDLL('user32');user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
                user.PostMessageW(owned_settings['hwnd'],0x0010,0,0)
            if notification_fixture:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,NOTIFICATION_KEY) as key:
                    if notification_before is None:
                        try:winreg.DeleteValue(key,'ToastEnabled')
                        except FileNotFoundError:pass
                    else:winreg.SetValueEx(key,'ToastEnabled',0,notification_before[1],notification_before[0])
                row['notification_registry_restored']=True
            row['seconds']=round(time.monotonic()-started,3)
            row['input_bytes_preserved']=all(p.is_file() and hash_file(p)==h for p,h in input_hashes.items())
            save(folder/'timings.json',timings)
            row['component_seconds']={lane:round(sum(t['seconds'] for t in timings if t['lane']==lane),3)
                                      for lane in ['uia','planner','jev']}
            save(folder/'result.json',row);summary['results'].append(row)
            summary['attempted']=len(summary['results']);summary['passed']=sum(r['passed'] for r in summary['results'])
            save(output/'summary.json',summary);print(json.dumps(row),flush=True)
        if abort:
            summary['aborted']='Previous native worker could not stop; remaining tasks not started'
            save(output/'summary.json',summary)
            break
    (output/'done').write_text('done',encoding='utf-8')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--select',type=int,nargs='+',choices=range(1,6))
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with (args.output.parent/(args.output.name+'-stacks.log')).open('w') as diagnostic:
        faulthandler.enable(file=diagnostic)
        faulthandler.dump_traceback_later(120,repeat=True,file=diagnostic)
        try:summary=run(args.bundle,args.output,args.select)
        finally:faulthandler.cancel_dump_traceback_later()
    raise SystemExit(0 if summary['passed']==summary['planned'] else 1)
