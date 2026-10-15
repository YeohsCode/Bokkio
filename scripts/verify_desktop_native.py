"""Real OS input -> passive recording -> replay, using an owned editor document."""
from __future__ import annotations
import argparse,json,sys,time,platform
from pathlib import Path
from bokkio.app_launch import installed_running_apps
from bokkio.audit import identifier
from bokkio.local_runtime import LocalRuntime
from bokkio.runtime import Runtime
from bokkio.sdk import Client
from bokkio.manual_recording import ManualRecorder
from bokkio.runtime_workflow import WorkflowLibrary,RuntimeWorkflowRunner,runtime_snapshot,window_identity

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--app',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--value',default='Bokkio 系统输入回放');p.add_argument('--demonstrate-only',action='store_true');p.add_argument('--reset-only',action='store_true');p.add_argument('--read-only',action='store_true');args=p.parse_args()
    root=args.output/identifier();root.mkdir(parents=True,mode=0o700);report={'platform':sys.platform,'architecture':platform.machine(),'human_input':False,'checks':[],'receipts':[]};rec=None;actor=None;replay=None
    def check(name,passed):report['checks'].append({'case':name,'passed':bool(passed)})
    try:
        matches=[a for a in installed_running_apps() if a['name'].casefold()==args.app.casefold()]
        if len(matches)!=1:raise ValueError('Open exactly one instance of the owned editor application')
        app=matches[0];actor=Client(LocalRuntime(root/'actor'));actor.open()
        windows=actor.call('desktop.windows',{'app':str(app['pid'])})['result'];windows=[w for w in windows if w['role']=='window' and not w.get('minimized')]
        if len(windows)!=1:raise ValueError('Use one owned document window for this acceptance test')
        anchor=window_identity(windows[0])
        def current():
            rows=actor.call('desktop.windows',{'app':str(app['pid'])})['result'];window=next(w['name'] for w in rows if window_identity(w)==anchor)
            observed,snapshot=runtime_snapshot(actor,app['pid'],window)
            fields=[n for n in snapshot['windows'] if n['role'] in {'text_area','text_field','document'} and 'set_value' in n['actions']]
            preferred=[n for n in fields if n['role'] in {'text_area','document'}]
            if len(preferred or fields)!=1:raise ValueError('Editor target is ambiguous')
            return window,observed,(preferred or fields)[0]
        def reset():
            window,observed,target=current();r=actor.call('desktop.act',{'app':str(app['pid']),'window':window,'observation_id':observed['result']['observation_id'],'ref':target['ref'],'action':'set_value','value':''})
            if r['status'] not in {'executed','verified'}:raise ValueError(r)
            check('reset_independently_read_empty',current()[2]['value']=='')
        if args.read_only:
            check('independent_readback',current()[2]['value']==args.value)
            return 0 if report['checks'][-1]['passed'] else 1
        reset()
        if args.reset_only:return 0
        if not args.demonstrate_only:
            reader=Client(Runtime(root/'recorder',{'apps':[str(app['pid'])],'write':False}));reader.open();rec=ManualRecorder(reader,[app],args.app+' · 输入与回放');rec.start();time.sleep(.7)
        combo='Command+A' if sys.platform=='darwin' else 'Ctrl+A'
        for action,arguments in [('click',{}),('key',{'key':combo}),('type',{'value':args.value}),('key',{'key':'Right'})]:
            window,observed,target=current();r=actor.call('desktop.input',{'app':str(app['pid']),'window':window,'observation_id':observed['result']['observation_id'],'ref':target['ref'],'action':action,**arguments});report['receipts'].append({k:r.get(k) for k in ('status','dispatched','error_code')})
            if r['status'] not in {'executed','verified'}:raise ValueError(r)
            time.sleep(.4)
        time.sleep(.5);check('OS_input_independent_readback',current()[2]['value']==args.value)
        if rec:
            preview=rec.stop();report['recording_issues']=preview['issues'];doc=preview['document'];report['recorded_steps']=len(doc['steps'])
            check('record_literal_value',any(s['action']=='set_value' and s['arguments']['value']==args.value for s in doc['steps']))
            check('record_key_combination',any(s['action']=='key' and s['arguments']['key']==combo for s in doc['steps']))
            check('record_arrow',any(s['action']=='key' and s['arguments']['key']=='Right' for s in doc['steps']))
            check('no_recording_issues',not preview['issues']);check('recorder_never_dispatches',not any(e['data'].get('write') for e in reader.runtime.store.query(kind='execution.intent')))
            library=WorkflowLibrary(root/'workflows');doc=library.save(doc);reset();runtime=LocalRuntime(root/'replay');runtime.policy['launch_apps']=doc['apps'];replay=Client(runtime);replay.open(apps=[]);runner=RuntimeWorkflowRunner(replay,root/'runs');run=runner.run(runner.start(doc,speed=5)['id']);report['replay_status']=run['status'];report['replay_error']=run.get('error')
            check('workflow_completed',run['status']=='completed');check('replay_from_empty_independent_readback',current()[2]['value']==args.value)
    except Exception as error:report['error']=str(error)
    finally:
        if rec and rec.state in {'recording','paused'}:rec.stop()
        if actor:actor.call('session.close')
        if replay:replay.call('session.close')
        report['passed']=sum(c['passed'] for c in report['checks']);report['total']=len(report['checks']);(root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'output':str(root),'passed':report['passed'],'total':report['total'],'error':report.get('error')},ensure_ascii=False),flush=True)
    return 0 if report['checks'] and all(c['passed'] for c in report['checks']) and not report.get('error') else 1
if __name__=='__main__':raise SystemExit(main())
