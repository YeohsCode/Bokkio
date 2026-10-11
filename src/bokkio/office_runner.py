"""Microsoft Office native pilot runner, with fail-closed input preflight."""
from __future__ import annotations

import copy
import ctypes as c
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import time
from urllib.parse import unquote,urlparse

from .model import BokkioError
from .office_benchmark import TASKS,digest,evaluate,load_bundle
from .workflow import save_json


def input_environment():
    if sys.platform!='darwin':return {'ready':False,'reason':'This pilot adaptation targets macOS'}
    cg=c.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
    cf=c.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    ax=c.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    cg.CGSessionCopyCurrentDictionary.restype=c.c_void_p
    cg.CGPreflightScreenCaptureAccess.restype=c.c_bool
    cg.CGPreflightPostEventAccess.restype=c.c_bool
    ax.AXIsProcessTrusted.restype=c.c_bool
    cf.CFDictionaryGetValue.argtypes=[c.c_void_p,c.c_void_p];cf.CFDictionaryGetValue.restype=c.c_void_p
    cf.CFStringCreateWithCString.argtypes=[c.c_void_p,c.c_char_p,c.c_uint];cf.CFStringCreateWithCString.restype=c.c_void_p
    cf.CFBooleanGetValue.argtypes=[c.c_void_p];cf.CFBooleanGetValue.restype=c.c_bool
    cf.CFRelease.argtypes=[c.c_void_p]
    session=cg.CGSessionCopyCurrentDictionary();locked=None
    if session:
        key=cf.CFStringCreateWithCString(None,b'CGSSessionScreenIsLocked',0x08000100)
        value=cf.CFDictionaryGetValue(session,key);locked=cf.CFBooleanGetValue(value) if value else False
        cf.CFRelease(key);cf.CFRelease(session)
    permissions={'ax':ax.AXIsProcessTrusted(),'capture':cg.CGPreflightScreenCaptureAccess(),'events':cg.CGPreflightPostEventAccess()}
    return {'ready':bool(session) and locked is False and all(permissions.values()),'session_available':bool(session),
            'session_locked':locked,'permissions':permissions,
            'reason':'interactive_session_unavailable' if not session or locked is not False else 'permissions_required' if not all(permissions.values()) else None}


def _load(workspace):
    root=Path(workspace).resolve();state=json.loads((root/'prepared.json').read_text(encoding='utf-8'))
    if state.get('schema')!='bokkio.office_pilot.v1' or state.get('revision')!='fbccd464f94fec9e284e139f97bf96d0b192f580':
        raise BokkioError('Unrecognized Office pilot preparation')
    bundle=Path(state['bundle']);load_bundle(bundle)
    if digest(bundle/'manifest.json')!=state['bundle_manifest_sha256']:
        raise BokkioError('Office task manifest changed after preparation')
    if len(state.get('tasks',[]))!=3 or {t['task_id'] for t in state['tasks']}!=set(TASKS):
        raise BokkioError('Prepared Office selection changed')
    for task in state['tasks']:
        spec=TASKS[task['task_id']];folder=root/task['task_id']/'desktop'
        if Path(task['desktop']).resolve()!=folder or Path(task['artifact']).resolve()!=folder/spec['file'] or task['app']!=spec['app'] or task['max_steps']!=15:
            raise BokkioError('Office task scope or budget changed')
        for name,record in task['initial_inputs'].items():
            source=Path(task['source']).resolve()
            base=root/task['task_id']
            candidate=folder/name if (folder/name).is_file() else base/name
            if Path(name).name!=name or not source.is_relative_to(base) or candidate.resolve()!=source or digest(candidate)!=record['sha256']:
                raise BokkioError('Office input changed before execution')
    return root,state


def _native_run(task,trace_path):
    import xa11y
    from .agent import DesktopAgent
    from .planner import OpenRouterPlanner
    from .jev import JevProvider
    from .xa11y_backend import Xa11yBackend
    from .selector import flatten
    from .macos_activation import activate_window
    file=Path(task['artifact']);app_name=task['app']
    # Opening reviewed synthetic inputs belongs to initialization and is
    # separately reported. No output is generated through file libraries.
    command=['/usr/bin/open','-a',app_name]
    command.append(task['source'])
    subprocess.run(command,check=True,timeout=20)
    app=xa11y.App.by_name(app_name,timeout=15)
    time.sleep(.5)
    stems={file.stem.casefold(),Path(task['source']).stem.casefold()}
    documents={str(Path(task['source']).resolve()),str(file.resolve())}
    class ScopedOffice(Xa11yBackend):
        supports_stale_refresh=True
        def _app_tree(self,app,live=None):
            if not input_environment()['ready']:
                raise BokkioError('Office interactive session changed; unlock before observing or dispatching')
            root=super()._app_tree(app,live)
            def prune(node,in_window=False,save_panel=False):
                node=copy.deepcopy(node)
                role=node['role'];name=(node.get('name') or '').casefold()
                if 'recent' in name or '最近' in name:return None
                # This task owns the initialized scratch file. A second new
                # document has no task-bound file identity or capture scope.
                if task['task_id']=='win_pro_l1_003' and role=='menu_item' and name in {'new presentation','new from template...'}:return None
                save_panel=save_panel or (role=='dialog' and name in {'save','save as','save as...'})
                # Expanded NSSavePanel browsers include ancestor directories
                # and unrelated filenames. Only the named path controls are
                # needed for this exact-output pilot; omit browser rows.
                if save_panel:
                    data=node['platform_data']
                    if data.get('native_file_entry') and str(Path(data['ax_url_path']).resolve())!=str(Path(task['desktop']).resolve()):return None
                    if role=='text_field' and not node.get('name'):return None
                if role in {'window','dialog'}:
                    allowed=in_window or any(stem in name for stem in stems) or name in {'font','paragraph','format cells','save as','save','open','styles','new presentation','new slide','slide layout','layout'}
                    document=node['platform_data'].get('ax_document')
                    if document:
                        allowed=str(Path(unquote(urlparse(document).path)).resolve()) in documents
                    if not allowed:return None
                    in_window=True
                if node['parent'] is not None and role not in {'window','dialog','menu','menu_bar','menu_item'} and not in_window:
                    return None
                node['children']=[p for child in node.get('children',[]) if (p:=prune(child,in_window,save_panel)) is not None]
                return node
            scoped=prune(root)
            if not any(n['role'] in {'window','dialog'} for n in flatten([scoped])):
                raise BokkioError('No authorized benchmark document/window is open; no private startup context is sent to models')
            for node in flatten([scoped]):
                if (node['role']=='window' and node['platform_data'].get('ax_document')
                        and Path(task['source']).resolve()==file.resolve()):
                    node['platform_data']['save_in_place_document']=True
                if task['task_id']=='win_pro_l1_003' and node['role'] in {'text_field','combo_box'} and (node['name'] or '').casefold().startswith('search'):
                    node['actions']=[]
                if node['role']=='combo_box' and node['platform_data'].get('ax_value_settable') and 'AXConfirm' in node['platform_data'].get('ax_original_actions',[]):
                    node['platform_data']['value_submission']='set_value_commits_via_bound_visual_input'
            editors=[n for n in flatten([scoped]) if n['role']=='text_area']
            indexed={n['ref']:n for n in flatten([scoped])}
            # Toolbar and native menu aliases can divide target confidence.
            # Keep one bound menu transport, while retaining save-panel Save.
            if any(n['role']=='menu_item' and n['name']=='Save' and n['platform_data'].get('native_menu_command') for n in indexed.values()):
                for node in indexed.values():
                    if node['role']!='button' or node['name']!='Save':continue
                    ancestor=node
                    while ancestor['parent'] in indexed and ancestor['role'] not in {'window','dialog'}:ancestor=indexed[ancestor['parent']]
                    if ancestor['role']!='dialog':node['actions']=[]
            if app_name=='Microsoft Word':
                # This pilot's declared input structure is one title paragraph
                # followed by body paragraphs. Bind those selection targets to
                # current readable native text, never fixture answer constants.
                readable=[n for n in editors if isinstance(n.get('value'),str) and 'select_text' in n['actions']]
                if len(readable)==1:
                    title,separator,body=readable[0]['value'].partition('\n')
                    if separator and title and body and len(title)<=4000 and len(body)<=4000:
                        readable[0]['platform_data']['selection_targets']={'main_title':title,'body':body}
                for node in indexed.values():
                    if node['role']=='button' and node['name']=='Clear Formatting':
                        node['platform_data']['click_transport']='selection_bound_pointer'
                    if node['role']=='combo_box' and node['name']=='Line and Paragraph Spacing':
                        node['actions']=[]
                        node['platform_data']['value_submission']='exact_spacing_requires_Paragraph_dialog'
            cjk_selection=any(any('\u3400'<=ch<='\u9fff' for ch in (n['state'].get('selected_text') or '')) for n in editors)
            if app_name=='Microsoft Word' and cjk_selection:
                for node in flatten([scoped]):
                    if node['role']=='combo_box' and node['name']=='Font:':
                        node['actions']=[a for a in node['actions'] if a not in {'set_value','submit','expand'}]
                        node['platform_data']['value_submission']='script_specific_font_dialog_required'
            for dialog in flatten([scoped]):
                if dialog['role']=='dialog' and dialog['name'] in {'Font','Paragraph'}:
                    for node in flatten([dialog]):
                        if node['role'] in {'combo_box','text_field'} and node['platform_data'].get('ax_value_settable'):
                            node['platform_data']['value_submission']='set_value_requires_dialog_commit'
                        if dialog['name']=='Font' and node['role']=='combo_box' and node['name']=='Latin text font:':
                            node['actions']=[] if node['state'].get('expanded') else ['expand']
                            node['platform_data']['mac_verified_actions']=node['actions']
                            node['platform_data']['value_submission']='native_popup_selection_required'
            return scoped
        def visual_value_replace(self,app,node,scope,value):
            from .office_visual import replace_combo
            if scope['role']=='dialog' and scope['name'] in {'Font','Paragraph'}:
                if scope['name']=='Font' and node['name']=='Size:':return self._native.perform(node,'set_value',value)
                return replace_combo(bound_pid,scope['name'],node,value,backend=self,confirm=False)
            if scope['role']!='window' or not any(stem in (scope['name'] or '').casefold() for stem in stems):
                raise BokkioError('Office visual field input requires the authorized document window')
            return replace_combo(bound_pid,scope['name'],node,value,backend=self)
        def visual_expand(self,app,node,scope):
            if scope['role']=='dialog' and scope['name']=='Font' and node['name']=='Latin text font:':
                from .office_visual import expand_combo
                return expand_combo(bound_pid,scope['name'],node,backend=self)
            return self._native.perform(node,'expand')
        def visual_click(self,app,node,scope):
            if app_name!='Microsoft Word' or node['name']!='Clear Formatting' or scope['role']!='window':
                raise BokkioError('Office button transport is outside the authorized body-format action')
            from .office_visual import click_selection_button
            document=scope['platform_data'].get('ax_document')
            return click_selection_button(bound_pid,scope['name'],node,backend=self,
                                          document=unquote(urlparse(document).path) if document else None)
        def visual_option_select(self,app,node,scope):
            if scope['role']!='dialog' or scope['name']!='Font':
                raise BokkioError('Office native option input requires the observed Font dialog')
            from .office_visual import select_option
            return select_option(bound_pid,scope['name'],node,backend=self)
        def perform(self,app,action,**arguments):
            if not str(app).isdigit() or int(app)!=bound_pid:raise BokkioError('Office action app is outside the task binding')
            snapshot=self.snapshot(app,arguments.get('window'))
            nodes={n['ref']:n for n in flatten(snapshot['windows'])}
            ref=arguments.get('ref');name=(nodes.get(ref,{}).get('name') or '').casefold()
            if nodes.get(ref,{}).get('platform_data',{}).get('native_menu_command'):
                main=[n for n in nodes.values() if n['role']=='window' and n['platform_data'].get('ax_document') and n['state'].get('active') is True]
                if not snapshot['app'].get('is_foreground') or len(main)!=1:
                    from .model import BokkioStaleSnapshot
                    raise BokkioStaleSnapshot('Owned Office main document or foreground changed before menu dispatch')
            if any(term in name for term in ['share','send','publish','共享','发送']):raise BokkioError('External communication is outside this Office pilot')
            if task['task_id']=='win_pro_l1_003' and name.startswith('search') and action in {'set_value','type','submit'}:
                raise BokkioError('PowerPoint application search is outside the title-slide task')
            if app_name=='Microsoft Word' and action!='select_text' and name in {'styles','font:','font size:','font...','paragraph...','clear formatting','line and paragraph spacing'}:
                editors=[n for n in nodes.values() if n['role']=='text_area' and 'select_text' in n['actions']]
                if editors and not any(n['state'].get('selected_text') for n in editors):
                    raise BokkioError('Word formatting requires a verified nonempty document text selection before dispatch')
            return super().perform(app,action,**arguments)
    bound_pid=app.pid
    backend=ScopedOffice()
    # Preflight precedes provider construction: inaccessible UI incurs no model
    # calls and is an environment result, not a model/task failure.
    backend.snapshot(str(bound_pid))
    owned_windows=[w for w in flatten(backend.snapshot(str(bound_pid))['windows'])
                   if w['role']=='window' and w['platform_data'].get('ax_document')
                   and str(Path(unquote(urlparse(w['platform_data']['ax_document']).path)).resolve())==str(Path(task['source']).resolve())]
    if len(owned_windows)!=1:raise BokkioError('Benchmark initialization requires one document bound to its exact source path')
    activation=activate_window(bound_pid,owned_windows[0]['name'],document=str(Path(task['source']).resolve()),clear_hover=True)
    if task['task_id']=='win_pro_l1_003':
        from .office_visual import OfficeVisualBackend
        from .visual_runtime import WindowScope
        backend=OfficeVisualBackend(backend,WindowScope('macos',bound_pid,owned_windows[0]['name'],activation['window_id'],str(Path(task['source']).resolve())))
    started=time.time_ns()
    def verify_artifact(trace):
        score=evaluate(task['task_id'],file)
        score['saved_after_start']=file.is_file() and file.stat().st_mtime_ns>started
        return score['passed'] and score['saved_after_start'], {'artifact':str(file),'score':score}
    agent=DesktopAgent(backend,OpenRouterPlanner(),JevProvider(),max_actions=15,max_replans=1,max_phases=8,final_verifier=verify_artifact)
    return agent.run(task['goal'],[str(bound_pid)],trace_path)


def run(workspace,*,environment=None,executor=None):
    root,state=_load(workspace);report_path=root/'run.json'
    if report_path.exists():raise BokkioError('Office run already exists; prepare a fresh workspace')
    environment=input_environment if environment is None else environment
    executor=_native_run if executor is None else executor
    env=environment()
    apps={}
    for spec in TASKS.values():
        plist=Path('/Applications')/(spec['app']+'.app')/'Contents/Info.plist'
        apps[spec['app']]={'installed':plist.is_file()}
        if plist.is_file():apps[spec['app']]['version']=plistlib.loads(plist.read_bytes()).get('CFBundleShortVersionString')
    report={'schema':'bokkio.office_pilot_run.v1','revision':state['revision'],'scope':state['scope'],
            'environment':env,'applications':apps,'planned':3,'started':0,'tasks':[],
            'official_score':False,'judge_status':'upstream_rubric_pinned_not_official_VLM_execution',
            'started_at_unix_ns':time.time_ns(),'setup_input_open_is_not_agent_action':True}
    if not env['ready']:
        report.update(status='blocked',blocked=3)
        report['tasks']=[{'task_id':t['task_id'],'status':'not_started','reason':env['reason'],'score':None} for t in state['tasks']]
        save_json(report_path,report);return report
    save_json(report_path,{**report,'status':'running'})
    for task in state['tasks']:
        if not environment()['ready']:
            report['tasks'].append({'task_id':task['task_id'],'status':'not_started','reason':'input_session_changed','score':None});continue
        report['started']+=1;started=time.time_ns();trace_path=root/task['task_id']/'agent.json'
        try:
            trace=executor(task,trace_path)
            row={'task_id':task['task_id'],'execution_status':trace['status'],'actions':trace.get('actions'),
                 'status':'executed','trace':str(trace_path.relative_to(root))}
        except Exception as error:
            row={'task_id':task['task_id'],'status':'environment_or_execution_error','reason':str(error),'score':None}
        if row['status']=='executed':
            score=evaluate(task['task_id'],task['artifact'])
            file=Path(task['artifact']);persisted_change=file.is_file() and file.stat().st_mtime_ns>started
            # The initial Word/Excel content must not be mistaken for a saved
            # solution merely because it already exists in the setup folder.
            score['saved_after_start']=persisted_change;score['passed']=score['passed'] and persisted_change
            row['score']=score
        report['tasks'].append(row);save_json(report_path,{**report,'status':'running'})
    report.update(status='completed' if report['started']==3 and all(t['status']=='executed' for t in report['tasks']) else 'incomplete',
                  passed=sum(bool(t.get('score') and t['score']['passed']) for t in report['tasks']))
    save_json(report_path,report);return report
