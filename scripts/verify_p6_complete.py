"""Windows P6 closure: real-app parameters, process resume and model repair.

Setup owns disposable files/windows. Only semantic native actions write outputs.
Every failed attempt persists its own summary; benchmark grading is separate.
"""
import argparse
import copy
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from bokkio.model import BokkioError, tree_digest
from bokkio.selector import flatten
from bokkio.workflow import (Recorder, WorkflowReplay, WorkflowScope, bind_parameters, digest,
                             from_agent_trace, make_workflow, parameterize, request_repair, save_json)
from bokkio.workflow_inputs import file_version
from bokkio.workflow_repair import OpenRouterWorkflowRepair
from bokkio.xa11y_backend import Xa11yBackend
from verify_waa_longchain import native_windows


def sha(data):return hashlib.sha256(data).hexdigest()


def close_window(window):
    user=ctypes.WinDLL('user32');user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    user.PostMessageW(window['hwnd'],0x10,0,0)


def open_explorer(folder):
    import xa11y
    before={w['hwnd'] for w in native_windows()}
    subprocess.Popen(['explorer.exe',str(folder)])
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        matches=[w for w in native_windows() if w['hwnd'] not in before and w['title']==folder.name+' - File Explorer']
        if len(matches)==1:
            xa11y.App.by_pid(matches[0]['pid'],timeout=20);return matches[0]
        time.sleep(.2)
    raise BokkioError('Owned Explorer window did not appear')


def open_notepad(path=None):
    import xa11y
    process=subprocess.Popen(['notepad.exe',*([str(path)] if path else [])])
    xa11y.App.by_pid(process.pid,timeout=20);time.sleep(.5);return process


def stop(process):
    if process is not None and process.poll() is None:process.terminate();process.wait(timeout=10)


def prepare_case(root,name):
    folder=root/name;folder.mkdir()
    source=folder/f'source-{name}.txt';source.write_bytes(('Source '+name).encode())
    return folder,source,folder/f'report-{name}.txt','P6 report '+name+'.'


def bindings_for(explorer,note):
    return {'explorer':str(explorer['pid']),'notepad':str(note.pid)},{'explorer':f"hwnd:0x{explorer['hwnd']:x}"}


def display_name(snapshot,source):
    names=[n['name'] for n in flatten(snapshot['windows']) if n['role']=='list_item'
           and n['name'] in {source.name,source.stem}]
    if len(names)!=1:raise BokkioError('Source row was not uniquely observed')
    return names[0]


def slots_for(workflow,literals):
    from bokkio.workflow_inputs import parameter_slot
    slots={}
    def visit(value,parts):
        if isinstance(value,dict):
            for k,v in value.items():visit(v,parts+[k])
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,parts+[str(i)])
        elif isinstance(value,str) and value in literals and parameter_slot(parts):slots['/'+'/'.join(parts)]=literals[value]
    visit(workflow,[]);return slots


def child(job_path):
    job=json.loads(job_path.read_text());workflow=json.loads(Path(job['workflow']).read_text())
    backend=WorkflowScope(Xa11yBackend(),job['bindings'],job['windows'])
    count=[0];after=[False];perform=backend.perform
    def dispatch(*a,**kw):result=perform(*a,**kw);count[0]+=1;return result
    backend.perform=dispatch
    def control():
        if not job.get('pause_after') or count[0]<job['pause_after']:return None
        if not after[0]:after[0]=True;return None  # verify the last action, pause at the next step
        return 'pause'
    resume=json.loads(Path(job['resume']).read_text()) if job.get('resume') else None
    run=WorkflowReplay(backend,control=control,timeout=10).run(workflow,job['bindings'],job['output'],parameters=job['parameters'],resume=resume)
    print(json.dumps({'status':run['status'],'steps':len(run['steps']),'reason':run.get('reason')}),flush=True)
    return 0 if run['status'] in {'completed','paused'} else 1


def run_child(root,name,workflow,bindings,windows,values,*,pause_after=None,resume=None):
    job={'workflow':str(workflow),'bindings':bindings,'windows':windows,'parameters':values,
         'output':str(root/f'{name}.json'),'pause_after':pause_after,'resume':str(resume) if resume else None}
    path=root/f'{name}-job.json';save_json(path,job)
    result=subprocess.run([sys.executable,__file__,'--child',str(path)],capture_output=True,text=True,timeout=600)
    (root/f'{name}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    if not Path(job['output']).is_file():raise BokkioError('Workflow child did not persist a run')
    return json.loads(Path(job['output']).read_text())


def values_for(backend,bindings,folder,source,report,body):
    source_label=display_name(backend.snapshot(bindings['explorer']),source)
    return {'source_name':source_label,'report_name':report.name if source_label==source.name else report.stem,
            'folder_title':folder.name+' - File Explorer','folder_name':folder.name,'body':body,'save_path':str(report),
            'source_path':str(source),'source_hash':sha(source.read_bytes()),'output_hash':sha(body.encode())}


def check_business(backend,bindings,source,report,body):
    version=file_version(report)
    rows=flatten(backend.snapshot(bindings['explorer'])['windows'])
    exists=any(n['role']=='list_item' and n['name'] in {report.name,report.stem} and n['state'].get('selected') for n in rows)
    reopened=None
    try:
        reopened=open_notepad(report)
        snapshot=Xa11yBackend().snapshot(str(reopened.pid))
        text=any(n['role']=='text_area' and n['value']==body for n in flatten(snapshot['windows']))
    finally:stop(reopened)
    return {'output':version,'artifact_matches':report.read_bytes()==body.encode(),
            'source_preserved':source.is_file(),'explorer_report_selected':exists,'reopened_native_text_matches':text}


def run(output,fixture,trace_path):
    if not output.resolve().is_relative_to(Path(r'C:\BokkioTasks').resolve()):raise BokkioError('Output must be disposable')
    output.mkdir(exist_ok=False,parents=True)
    source_paths=[Path(__file__),*[Path(__file__).parents[1]/'src/bokkio'/n for n in
        ['workflow.py','workflow_inputs.py','workflow_repair.py','cli.py','agent.py','planner.py','xa11y_backend.py','windows_uia.py']]]
    summary={'scope':'native_p6_closure','planned':{'parameter_cases':3,'resume_cases':1,'wrapper_cases':1,'model_repairs':1,'client_receipts':2},
        'parameters':[],'resume':None,'wrapper':None,'model_repair':None,'source_sha256':{p.name:sha(p.read_bytes()) for p in source_paths},
        'fixture_sha256':sha(fixture.read_bytes()),'input_trace_sha256':sha(trace_path.read_bytes())}
    def persist():save_json(output/'summary.json',summary)
    persist();note=None;explorer=None;main=None
    try:
        # Build a real cross-app Workflow: native Explorer source selection,
        # the five-step successful Notepad save, then Explorer output selection.
        folder,source,report,body=prepare_case(output,'baseline')
        explorer=open_explorer(folder);note=open_notepad();bindings,windows=bindings_for(explorer,note)
        backend=WorkflowScope(Xa11yBackend(),bindings,windows);values=values_for(backend,bindings,folder,source,report,body)
        recorder=Recorder(backend,bindings)
        def capture_file(label,intent):
            before=backend.snapshot(bindings['explorer'])
            result=backend.perform(bindings['explorer'],'select',role='list_item',name=label,expected_snapshot=tree_digest(before['windows']))
            after=backend.snapshot(bindings['explorer'])
            recorder.capture_receipt('explorer',intent=intent,before=before,result=result,after=after)
            save_json(output/'client-recording.json',recorder.events)
            summary['baseline']={'client_receipts':len(recorder.steps)};persist()
            return copy.deepcopy(recorder.steps[-1])
        first=capture_file(values['source_name'],'Select the source file before creating its report')
        trace=json.loads(trace_path.read_text())
        note_workflow=from_agent_trace(trace,'Notepad save from successful P5 trace',{a:'notepad' for a in trace['apps']})
        original_path=next(s['arguments']['value'] for s in note_workflow['steps'] if s['action']=='set_value' and s['target']['name']=='File name:')
        note_template=parameterize(note_workflow,{'body':{'type':'string','max_length':4000},'path':{'type':'path','max_length':4096}},
            slots_for(note_workflow,{'This is a draft.':'body',original_path:'path'}))
        note_run=WorkflowReplay(backend,timeout=10).run(note_template,{'notepad':bindings['notepad']},output/'baseline-notepad-run.json',parameters={'body':body,'path':str(report)})
        if note_run['status']!='completed':raise BokkioError('Baseline native Notepad recording failed')
        note_steps=bind_parameters(note_template,{'body':body,'path':str(report)})['steps']
        last=capture_file(values['report_name'],'Select the saved report in Explorer')
        steps=[first,*note_steps,last]
        for i,s in enumerate(steps):s['id']=f's{i+1}';s['depends_on']=[f's{i}'] if i else []
        literal=make_workflow('Native source to saved report',steps,'client_receipts_and_completed_agent_trace',
            metadata={'notepad_trace_sha256':sha(trace_path.read_bytes()),'client_receipts':2})
        declarations={k:{'type':'sha256' if k.endswith('_hash') else 'path' if k.endswith('_path') else 'string','max_length':4096} for k in values}
        template=parameterize(literal,declarations,slots_for(literal,{v:k for k,v in values.items()}),
            inputs=[{'id':'source','path':{'param':'source_path'},'sha256':{'param':'source_hash'}}],
            deliveries=[{'id':'report','path':{'param':'save_path'},'sha256':{'param':'output_hash'}}])
        workflow_path=output/'report-workflow.json';save_json(workflow_path,template)
        save_json(output/'client-recording.json',recorder.events);save_json(output/'literal-workflow.json',literal)
        summary['baseline']={'passed':note_run['status']=='completed' and report.read_bytes()==body.encode(),'client_receipts':2};persist()
        stop(note);note=None;close_window(explorer);explorer=None
        for name in ['alpha','beta space','gamma-punctuation']:
            folder,source,report,body=prepare_case(output,name)
            explorer=open_explorer(folder);note=open_notepad();bindings,windows=bindings_for(explorer,note)
            backend=WorkflowScope(Xa11yBackend(),bindings,windows);values=values_for(backend,bindings,folder,source,report,body)
            run_report=run_child(output,name,workflow_path,bindings,windows,values)
            if run_report['status']!='completed':
                summary['parameters'].append({'name':name,'status':run_report['status'],'passed':False,'reason':run_report.get('reason')});persist()
                raise BokkioError('Parameterized native replay failed in '+name)
            business=check_business(backend,bindings,source,report,body)
            business['source_preserved']=sha(source.read_bytes())==values['source_hash']
            row={'name':name,'status':run_report['status'],'dispatched':sum(s['dispatched'] for s in run_report['steps']),
                 'template_sha256':run_report['workflow_sha256'],'checks':business,
                 'passed':all(business[k] for k in ('artifact_matches','source_preserved','explorer_report_selected','reopened_native_text_matches'))}
            summary['parameters'].append(row);persist()
            stop(note);note=None;close_window(explorer);explorer=None
        folder,source,report,body=prepare_case(output,'resume')
        explorer=open_explorer(folder);note=open_notepad();bindings,windows=bindings_for(explorer,note)
        backend=WorkflowScope(Xa11yBackend(),bindings,windows);values=values_for(backend,bindings,folder,source,report,body)
        paused=run_child(output,'paused',workflow_path,bindings,windows,values,pause_after=6)
        if paused['status']!='paused':raise BokkioError('Native workflow did not pause at the intended boundary')
        previous_pid=note.pid;stop(note);note=open_notepad(report)
        bindings,windows=bindings_for(explorer,note);backend=WorkflowScope(Xa11yBackend(),bindings,windows)
        resumed=run_child(output,'resumed',workflow_path,bindings,windows,values,resume=output/'paused.json')
        new_steps=resumed['steps'][len([s for s in paused['steps'] if s['status']=='completed']):]
        business=check_business(backend,bindings,source,report,body) if resumed['status']=='completed' else {}
        summary['resume']={'paused_status':paused['status'],'resumed_status':resumed['status'],'previous_pid':previous_pid,'new_pid':note.pid,
            'new_dispatches':sum(s['dispatched'] for s in new_steps),'checks':business,
            'passed':resumed['status']=='completed' and previous_pid!=note.pid and sum(s['dispatched'] for s in new_steps)==1 and business.get('artifact_matches')};persist()
        if not summary['resume']['passed']:raise BokkioError('Native checkpoint resume failed')
        stop(note);note=None;close_window(explorer);explorer=None
        # Native structural change plus actual LLM selector repair, with no model in replay.
        import xa11y
        main=subprocess.Popen([str(fixture)]);xa11y.App.by_pid(main.pid,timeout=20);time.sleep(.5)
        fb={'fixture':str(main.pid)};scope={'fixture':'Bokkio interactions'};backend=WorkflowScope(Xa11yBackend(),fb,scope)
        recorder=Recorder(backend,fb)
        recorder.perform('fixture','set_value',intent='Write the Search field',role='text_field',name='Search',value='wrapper proof')
        one=recorder.export('Write Search');one['steps'][0]['target']['fallback']='named_context';one['sha256']=digest({k:v for k,v in one.items() if k!='sha256'})
        stop(main);main=subprocess.Popen([str(fixture)],env={**os.environ,'BOKKIO_FIXTURE_WRAP_SEARCH':'1'});xa11y.App.by_pid(main.pid,timeout=20);time.sleep(.5)
        fb={'fixture':str(main.pid)};backend=WorkflowScope(Xa11yBackend(),fb,scope)
        wrapped=WorkflowReplay(backend).run(one,fb,output/'wrapper-run.json');save_json(output/'wrapper-workflow.json',one)
        summary['wrapper']={'status':wrapped['status'],'lane':wrapped['steps'][0].get('selector',{}).get('lane'),
            'passed':wrapped['status']=='completed' and wrapped['steps'][0]['selector']['lane']=='named_context'};persist()
        if not summary['wrapper']['passed']:raise BokkioError('Native wrapper fallback was not exercised')
        bad=copy.deepcopy(one);bad['steps'][0]['target']['name']='Missing Search';bad['sha256']=digest({k:v for k,v in bad.items() if k!='sha256'})
        failed=WorkflowReplay(backend,timeout=0).run(bad,fb,output/'model-failed-run.json');save_json(output/'model-broken-workflow.json',bad)
        provider=OpenRouterWorkflowRepair(model='openai/gpt-4.1')
        repaired=request_repair(bad,failed,provider,'Recover the observed Search field after a selector change')
        save_json(output/'model-repaired-workflow.json',repaired)
        repaired_run=WorkflowReplay(backend).run(repaired,fb,output/'model-repaired-run.json')
        summary['model_repair']={'failed_dispatches':sum(s['dispatched'] for s in failed['steps']),
            'model_call':provider.last_call,'parent_sha256':repaired['parent_sha256'],'original_sha256':bad['sha256'],
            'replay_status':repaired_run['status'],'passed':repaired_run['status']=='completed' and repaired['parent_sha256']==bad['sha256']};persist()
        summary['passed']=all(r['passed'] for r in summary['parameters']) and all(summary[k]['passed'] for k in ('baseline','resume','wrapper','model_repair'))
        persist();return summary['passed']
    except Exception as error:
        summary['passed']=False;summary['error']=str(error);persist();raise
    finally:
        stop(note);stop(main)
        if explorer:close_window(explorer)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--fixture',type=Path)
    parser.add_argument('--agent-trace',type=Path)
    args=parser.parse_args()
    if args.child:raise SystemExit(child(args.child))
    if not all((args.output,args.fixture,args.agent_trace)):parser.error('output, fixture and agent-trace required')
    raise SystemExit(0 if run(args.output,args.fixture,args.agent_trace) else 1)
