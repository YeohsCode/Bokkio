"""Real macOS OS-event capture and replay on the lab; input is generated, not human."""
from pathlib import Path
import argparse,json,time,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bokkio.app_launch import installed_running_apps
from bokkio.manual_recording import ManualRecorder
from bokkio.runtime import Runtime
from bokkio.sdk import Client
from bokkio.audit import identifier
from bokkio.runtime_workflow import WorkflowLibrary,RuntimeWorkflowRunner,runtime_snapshot
from bokkio.workflow import save_json

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--approve-owned-fixture',action='store_true');args=p.parse_args()
if not args.approve_owned_fixture:p.error('Explicit owned fixture authorization is required')
root=args.output;root.mkdir(parents=True,exist_ok=False,mode=0o700)
app=next(a for a in installed_running_apps()if a['name']=='BokkioWorkflowLab' and a['path']==str(args.fixture.resolve()));pid=app['pid'];title='Bokkio Workflow Lab'
actor=Client(Runtime(root/'actor',{'apps':[str(pid)],'write':True,'require_approval':False}));actor.open()
reader=Client(Runtime(root/'recorder',{'apps':[str(pid)],'write':False}));reader.open()
rec=ManualRecorder(reader,[app]);report={'scope':'actual_OS_posted_pointer_keyboard_capture_not_human_demonstration','human_input':False,'checks':[],'input_receipts':[]}
def dump():
 report.update(passed=sum(c['passed']for c in report['checks']),total=len(report['checks']));save_json(root/'report.json',report)
def check(case,passed,**kw):report['checks'].append({'case':case,'passed':bool(passed),**kw});dump()
def command(action):save_json(Path('/tmp/bokkio-workflow-fixture/command.json'),{'id':identifier(),'action':action});time.sleep(.2)
try:
 command('reset');activated=actor.call('desktop.activate',{'app':str(pid),'window':title})
 if activated['status'] not in {'executed','verified'}:
  report.update(status='blocked',error_code=activated.get('error_code'),guard_bypassed=False);dump();raise SystemExit(2)
 rec.start();time.sleep(.6)
 for action,role,name,value in [('click','text_field','Workflow Input',None),('type','text_field','Workflow Input','physical 中文'),('click','button','Confirm',None)]:
  # Test-fixture preparation removes caret animation so the independent pixel
  # input guard can validate exact image bytes. No guard is disabled or relaxed.
  command('blur')
  for attempt in range(3):
   _,snap=runtime_snapshot(actor,pid,title);node=next(n for n in snap['windows']if n['role']==role and n['name']==name);b=node['bounds']
   observed=actor.call('desktop.capture',{'app':str(pid),'window':title});meta=observed['result']['metadata'];rect=meta['content_rect']
   x=(b['x']+b['width']/2-rect['x'])*meta['width']/rect['width'];y=(b['y']+b['height']/2-rect['y'])*meta['height']/rect['height']
   receipt=actor.call('desktop.pixel',{'app':str(pid),'window':title,'observation_id':observed['result']['observation_id'],'action':action,'x':x,'y':y,**({'value':value}if value is not None else{})})
   report['input_receipts'].append({k:receipt.get(k)for k in ['status','dispatched','error_code','operation_id']});dump()
   if receipt['status'] in {'executed','verified'}:break
   if receipt.get('dispatched') not in {False,0}:raise RuntimeError('Unknown input completion; never replay this request')
   if attempt==2:raise RuntimeError('Input remained unavailable after bounded zero-dispatch observations')
  time.sleep(.7)
 deadline=time.monotonic()+8
 while time.monotonic()<deadline and not any(s['action']=='click' and s['target']['name']=='Confirm'for s in rec.doc['steps']):time.sleep(.1)
 preview=rec.stop();actor.call('session.close');doc=preview['document'];save_json(root/'draft.json',doc)
 check('capture_actual_pointer_button',any(s['action']=='click' and s['target']['name']=='Confirm'for s in doc['steps']))
 check('capture_actual_OS_typed_value',any(s['action']=='set_value' and s['arguments']['value']=='physical 中文'for s in doc['steps']))
 check('no_recording_issues',not preview['issues'])
 check('recording_never_redispatches',not any(e['data'].get('write')for e in reader.runtime.store.query(kind='execution.intent')))
 command('reset');library=WorkflowLibrary(root/'workflows');doc=library.save(doc)
 grants={'apps':[app['name']],'launch_apps':doc['apps'],'write':True,'require_approval':False}
 c=Client(Runtime(root/'replay',grants));c.open(apps=[]);runner=RuntimeWorkflowRunner(c,root/'runs');run=runner.run(runner.start(doc)['id']);state=json.loads(Path('/tmp/bokkio-workflow-fixture/state.json').read_text())
 check('same_recorded_workflow_replays',run['status']=='completed' and state['input']=='physical 中文' and state['clicks']==1,replay_status=run['status'],steps=len(doc['steps']))
 c.call('session.close');report['status']='completed';dump()
except Exception as e:
 report.update(status='failed',error_type=type(e).__name__,error=str(e));dump()
finally:
 if rec.state in {'recording','paused'}:rec.stop()
 else:reader.call('session.close')
 save_json(root/'partial-draft.json',rec.preview())
 report['planned']=5
 report['not_run']=5-len(report['checks']);dump()
 actor.call('session.close')
print(json.dumps({'status':report.get('status'),'passed':report.get('passed'),'total':report.get('total')}))
raise SystemExit(0 if report.get('status')=='completed' and all(c['passed']for c in report['checks']) else 1)
