"""Record native click/type/select, replay across fresh processes, compile a P5 trace.

Fixture reset, process lifecycle and byte checks belong to the verifier. Every
recorded/replayed action is a semantic Runtime action; replay uses no models.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import time

from bokkio.model import BokkioError
from bokkio.selector import flatten
from bokkio.workflow import (Recorder,WorkflowReplay,from_agent_trace,make_workflow,
                             repair_version,save_json)
from bokkio.xa11y_backend import Xa11yBackend


def run(fixture, trace_path, output, replays=3):
    import xa11y
    output.mkdir(parents=True,exist_ok=False)
    source=json.loads(trace_path.read_text(encoding='utf-8'))
    workflow=from_agent_trace(source,'WAA draft from successful Agent trace',
                              {app:'notepad' for app in source['apps']})
    save_json(output/'agent-workflow.json',workflow)
    filename=[s['arguments']['value'] for s in workflow['steps']
              if s['action']=='set_value' and s['target']['name']=='File name:']
    if len(filename)!=1:raise BokkioError('Need one disposable draft path')
    draft=Path(filename[0])
    if draft.name!='draft.txt' or not draft.resolve().is_relative_to(Path(r'C:\BokkioTasks').resolve()):
        raise BokkioError('Trace deliverable is outside the disposable fixture')
    if draft.read_bytes()!=b'This is a draft.':raise BokkioError('Original Agent artifact did not pass byte check')
    original_bytes=draft.read_bytes();summary={'scope':'native_p6_development','recorded_replays':[],
                                              'agent_trace_replays':[],'repair':None,
        'planned':{'recorded_replays':replays,'agent_trace_replays':replays,'repair_replays':1},
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),*[Path(__file__).parents[1]/'src/bokkio'/n for n in
             ['workflow.py','workflow_inputs.py','workflow_repair.py','cli.py','agent.py','planner.py','xa11y_backend.py','windows_uia.py']]]},
        'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
        'agent_trace_sha256':hashlib.sha256(trace_path.read_bytes()).hexdigest()}
    save_json(output/'summary.json',summary)
    def start(exe):
        p=subprocess.Popen([str(exe)]);xa11y.App.by_pid(p.pid,timeout=20);time.sleep(0.5);return p
    def close(procs):
        for p in procs:
            if p.poll() is None:p.terminate();p.wait(timeout=10)
    raw_backend=Xa11yBackend();fixture_pids=set()
    class ScopedNative:
        supports_action_observation = True
        def snapshot(self,app):
            return raw_backend.snapshot(app,'Bokkio interactions' if app in fixture_pids else None)
        def perform(self,app,action,**arguments):
            return raw_backend.perform(app,action,window='Bokkio interactions' if app in fixture_pids else None,**arguments)
    backend=ScopedNative();procs=[]
    try:
        main=start(fixture);note=start('notepad.exe');procs=[main,note]
        bindings={'fixture':str(main.pid),'notepad':str(note.pid)}
        fixture_pids.add(str(main.pid))
        backend.perform(bindings['fixture'],'set_value',role='text_field',name='Search',value='')
        recorder=Recorder(backend,bindings)
        recorder.perform('fixture','focus',intent='Focus Search',role='text_field',name='Search')
        recorder.perform('fixture','type',intent='Insert P6 repeatable',role='text_field',name='Search',
                         value='P6 repeatable',expected_value='P6 repeatable')
        recorder.perform('fixture','click',intent='Submit Search',role='button',name='Submit',
                         verify=[{'role':'static_text','name':'Submitted: P6 repeatable','field':'present','equals':True}])
        recorder.perform('fixture','expand',intent='Open Mode',role='combo_box',name='Mode')
        recorder.perform('fixture','select',intent='Select Second',role='list_item',name='Second')
        recorder.perform('notepad','set_value',intent='Write native cross-app output',
                         role='text_area',name='Text Editor',value='P6 native workflow')
        recorded=recorder.export('Native click type select and cross-app write')
        save_json(output/'recorded-workflow.json',recorded)
        save_json(output/'recording.json',recorder.events)
        close(procs);procs=[]
        for i in range(1,replays+1):
            main=start(fixture);note=start('notepad.exe');procs=[main,note]
            bindings={'fixture':str(main.pid),'notepad':str(note.pid)}
            fixture_pids.add(str(main.pid))
            report=WorkflowReplay(backend,timeout=5).run(recorded,bindings,output/f'replay-{i}.json')
            rows=flatten(backend.snapshot(bindings['fixture'])['windows'])
            notes=flatten(backend.snapshot(bindings['notepad'])['windows'])
            checks=[any(n['name']=='Submitted: P6 repeatable' for n in rows),
                    any(n['role']=='combo_box' and n['name']=='Mode' and n['value']=='Second' for n in rows),
                    any(n['role']=='text_area' and n['value']=='P6 native workflow' for n in notes)]
            row={'iteration':i,'status':report['status'],'native_dispatches':sum(s['dispatched'] for s in report['steps']),
                 'fallback_steps':sum(s.get('selector',{}).get('lane')=='role_name_context' for s in report['steps']),
                 'independent_checks':checks,'passed':report['status']=='completed' and all(checks)}
            summary['recorded_replays'].append(row);save_json(output/'summary.json',summary);print(json.dumps(row),flush=True)
            close(procs);procs=[]
        # A failed version is retained. A new version repairs the selector and
        # is explicitly replayed against fresh owned native state.
        bad_steps=copy.deepcopy(recorded['steps']);bad_steps[0]['target']['name']='Missing Search'
        bad=make_workflow(recorded['name'],bad_steps,recorded['source'])
        save_json(output/'broken-workflow.json',bad)
        main=start(fixture);note=start('notepad.exe');procs=[main,note]
        bindings={'fixture':str(main.pid),'notepad':str(note.pid)}
        fixture_pids.add(str(main.pid))
        failed=WorkflowReplay(backend,timeout=0).run(bad,bindings,output/'repair-failed-run.json')
        repaired=repair_version(bad,failed,recorded['steps'],'Restore Search selector from the verified native recording')
        save_json(output/'repaired-workflow.json',repaired)
        repaired_run=WorkflowReplay(backend).run(repaired,bindings,output/'repair-replay.json')
        summary['repair']={'failed_status':failed['status'],'failed_dispatches':sum(s['dispatched'] for s in failed['steps']),
                           'revision':repaired['revision'],'parent_sha256':repaired['parent_sha256'],
                           'replay_status':repaired_run['status'],'original_version_preserved':bad['sha256']==repaired['parent_sha256'],
                           'passed':failed['status']=='failed' and repaired_run['status']=='completed'}
        close(procs);procs=[]
        for i in range(1,replays+1):
            draft.unlink(missing_ok=True)
            note=start('notepad.exe');procs=[note]
            report=WorkflowReplay(backend).run(workflow,{'notepad':str(note.pid)},output/f'agent-replay-{i}.json')
            data=draft.read_bytes() if draft.is_file() else b''
            close(procs);procs=[]
            reopened=subprocess.Popen(['notepad.exe',str(draft)]);procs=[reopened]
            xa11y.App.by_pid(reopened.pid,timeout=20)
            nodes=flatten(backend.snapshot(str(reopened.pid))['windows'])
            reopen_check=any(n['role']=='text_area' and n['value']=='This is a draft.' for n in nodes)
            save_json(output/f'agent-reopened-{i}.json',backend.snapshot(str(reopened.pid)))
            row={'iteration':i,'status':report['status'],'native_dispatches':sum(s['dispatched'] for s in report['steps']),
                 'artifact_bytes':len(data),'artifact_sha256':hashlib.sha256(data).hexdigest(),
                 'reopened_native_text_matches':reopen_check,
                 'passed':report['status']=='completed' and data==original_bytes and reopen_check}
            summary['agent_trace_replays'].append(row);save_json(output/'summary.json',summary);print(json.dumps(row),flush=True)
            close(procs);procs=[]
        summary['passed']=all(r['passed'] for r in summary['recorded_replays']+summary['agent_trace_replays']) and summary['repair']['passed']
        save_json(output/'summary.json',summary)
        return summary['passed']
    except Exception as error:
        summary['passed']=False;summary['error']=str(error);save_json(output/'summary.json',summary)
        raise
    finally:
        close(procs)
        # Preserve the original P5 evidence artifact even if replay fails.
        draft.write_bytes(original_bytes)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--agent-trace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replays',type=int,choices=[1,3],default=3)
    args=parser.parse_args()
    raise SystemExit(0 if run(args.fixture,args.agent_trace,args.output,args.replays) else 1)
