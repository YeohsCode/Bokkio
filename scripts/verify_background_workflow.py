"""Background native desktop replay with an independent foreground/pointer witness."""
from pathlib import Path
import argparse,json,time,sys,os,signal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bokkio.app_launch import desktop_environment,installed_running_apps
from bokkio.runtime import Runtime,process_birth
from bokkio.sdk import Client
from bokkio.runtime_workflow import WorkflowLibrary,RuntimeWorkflowRunner
from bokkio.workflow import save_json

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--guard',type=Path,required=True);p.add_argument('--workflow',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--approve-owned-fixture',action='store_true');args=p.parse_args()
if not args.approve_owned_fixture:p.error('Explicit owned fixture authorization is required')
root=args.output;root.mkdir(parents=True,exist_ok=False,mode=0o700);doc=json.loads(args.workflow.read_text())
if any(g['name']!='BokkioWorkflowLab' or g['path']!=str(args.fixture.resolve())for g in doc['apps'].values()):raise ValueError('Only the owned Lab application is accepted')
# Ensure startup itself is exercised. The Lab contains no user documents.
for a in installed_running_apps():
 if a['name']=='BokkioWorkflowLab'and a['path']==str(args.fixture.resolve()):
  stamp=process_birth(a['pid']);probe=Client(Runtime(root/'ownership',{'apps':[str(a['pid'])]}));probe.open();r=probe.call('desktop.observe',{'app':str(a['pid']),'max_nodes':300});probe.call('session.close')
  if r['status']=='completed'and [n['name']for n in r['result']['nodes']if n['role']=='window']==['Bokkio Workflow Lab']and process_birth(a['pid'])==stamp:os.kill(a['pid'],signal.SIGTERM)
  else:raise ValueError('Lab ownership not verified')
guard={'name':'BokkioBackgroundGuard','path':str(args.guard.resolve()),'bundle_id':'local.bokkio.bokkiobackgroundguard'}
policy={'apps':['BokkioWorkflowLab',guard['name']],'launch_apps':{**doc['apps'],'witness':guard},'write':True,'require_approval':False}
c=Client(Runtime(root/'runtime',policy));c.open(apps=[]);receipt=c.call('desktop.launch',{'app':'witness'});pid=receipt['result']['pid']
deadline=time.monotonic()+12
while time.monotonic()<deadline:
    observation=c.call('desktop.observe',{'app':str(pid),'window':'Bokkio Runtime Contract','max_nodes':200})
    if observation['status']=='completed' and any(n['role']=='window'for n in observation['result']['nodes']):break
    time.sleep(.15)
else:raise RuntimeError('Foreground witness window did not become ready')
active=c.call('desktop.activate',{'app':str(pid),'window':'Bokkio Runtime Contract'})
if active['status']not in {'executed','verified'}:raise RuntimeError('Foreground witness could not be activated')
before=desktop_environment();assert before['foreground_pid']==pid
library=WorkflowLibrary(root/'workflows');doc=library.save(doc);runner=RuntimeWorkflowRunner(c,root/'runs');result=runner.run(runner.start(doc,'headless')['id']);after=desktop_environment();actual=json.loads(Path('/tmp/bokkio-workflow-fixture/state.json').read_text())
with c.runtime.store.connect()as db:
 tools=[r[0]for r in db.execute('SELECT tool FROM operations')]
checks=[{'case':'background_launch_and_full_recorded_replay','passed':result['status']=='completed'},{'case':'foreground_witness_unchanged','passed':before['foreground_pid']==after['foreground_pid']==pid},{'case':'pointer_unchanged','passed':before['pointer']==after['pointer']},{'case':'independent_field_and_button_state','passed':actual['input']=='physical 中文'and actual['clicks']==1},{'case':'no_pixel_or_activation_in_workflow','passed':all(e['data'].get('tool')not in {'desktop.pixel','desktop.activate'}for e in c.runtime.store.query(kind='request.received') if e['operation_id']not in {receipt['operation_id'],active['operation_id']})}]
c.call('session.close');report={'scope':'background_native_with_unlocked_interactive_desktop_not_displayless_execution','passed':sum(x['passed']for x in checks),'total':len(checks),'checks':checks,'run_status':result['status'],'error':result.get('error'),'initial_app_not_running':True,'no_foreground_or_pointer_fallback':True};save_json(root/'report.json',report);print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if all(x['passed']for x in checks)else 1)
