"""Owned macOS workflow integration matrix; physical/human capture is reported separately."""
from pathlib import Path
import argparse,json,os,signal,time,sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bokkio.app_launch import installed_running_apps
from bokkio.runtime import Runtime,process_birth
from bokkio.sdk import Client
from bokkio.audit import identifier
from bokkio.runtime_workflow import WorkflowLibrary,RuntimeWorkflowRunner,SCHEMA,runtime_snapshot
from bokkio.workflow import selector_for,save_json
from scripts.evaluate_runtime_business import web_server

def wait(fn,timeout=15):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            value=fn()
            if value:return value
        except (ValueError,FileNotFoundError):pass
        time.sleep(.1)
    raise TimeoutError('Owned fixture state did not settle')

def main(args):
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    control=Path('/tmp/bokkio-workflow-fixture');control.mkdir(exist_ok=True)
    grant={'name':'BokkioWorkflowLab','path':str(args.fixture.resolve()),'bundle_id':'local.bokkio.bokkioworkflowlab'}
    policy={'apps':[grant['name']],'launch_apps':{'lab':grant},'write':True,'require_approval':False}
    report={'scope':'owned_macOS_workflow_Runtime_integration_not_autonomous_business_benchmark','human_physical_recording_tested':False,'checks':[]}
    def command(action,**kw):
        save_json(control/'command.json',{'id':identifier(),'action':action,**kw});time.sleep(.15)
    def state():return json.loads((control/'state.json').read_text())
    def add(case,passed,**kw):
        report['checks'].append({'case':case,'passed':bool(passed),**kw});report.update(passed=sum(x['passed']for x in report['checks']),total=len(report['checks']));save_json(args.output/'report.json',report);print(json.dumps(report['checks'][-1]),flush=True)
    client=Client(Runtime(args.output/'runtime',policy));client.open(apps=[])
    launched=client.call('desktop.launch',{'app':'lab'});assert launched['status'] in {'executed','verified'},launched
    pid=launched['result']['pid'];wait(lambda:state()['pid']==pid)
    command('reset');observed,snapshot=runtime_snapshot(client,pid,'Bokkio Workflow Lab')
    field=next(n for n in snapshot['windows']if n['role']=='text_field' and n['name']=='Workflow Input')
    button=next(n for n in snapshot['windows']if n['role']=='button' and n['name']=='Confirm')
    def step(node,action,args,verify):
        target=selector_for(snapshot,node);target['identifier']=node['platform_data']['ax_identifier']
        return {'id':identifier(),'kind':'native','app':'lab','window':'Bokkio Workflow Lab','target':target,'action':action,'arguments':args,'wait':[],'verify':verify,'timeout':2}
    doc={'schema':SCHEMA,'id':identifier(),'name':'Owned native workflow','revision':1,'parent_sha256':None,'apps':{'lab':grant},'steps':[
        step(field,'set_value',{'value':'workflow 中文'},[{'role':'text_field','name':'Workflow Input','field':'value','equals':'workflow 中文'}]),
        step(button,'click',{},[{'role':'static_text','name':None,'field':'value','equals':'Confirmed 1'}])]}
    library=WorkflowLibrary(args.output/'workflows');doc=library.save(doc);runner=RuntimeWorkflowRunner(client,args.output/'runs')
    for i,(x,y) in enumerate([(120,300),(400,180),(650,400)]):
        command('reset');command('move',x=x,y=y);r=runner.run(runner.start(doc)['id']);actual=state()
        add('native_replay_moved_window_'+str(i+1),r['status']=='completed' and actual['input']=='workflow 中文' and actual['clicks']==1,status=r['status'],steps=len(r['steps']),operation_ids=[x['operation_id']for x in r['steps']])
    # Terminate only the verified dedicated fixture with the same birth identity.
    stamp=process_birth(pid);_,snapshot=runtime_snapshot(client,pid,'Bokkio Workflow Lab')
    if process_birth(pid)==stamp and sum(n['role']=='window'for n in snapshot['windows'])==1:os.kill(pid,signal.SIGTERM);wait(lambda:not any(a['pid']==pid for a in installed_running_apps()))
    r=runner.run(runner.start(doc)['id']);actual=state()
    add('app_not_running_auto_launch_new_pid',r['status']=='completed' and actual['pid']!=pid and actual['input']=='workflow 中文' and actual['clicks']==1,status=r['status'],new_pid_confirmed=actual['pid']!=pid)
    command('reset');command('duplicate');r=runner.run(runner.start(doc)['id']);actual=state()
    add('ambiguous_control_zero_dispatch',r['status']=='failed' and actual['input']=='' and actual['clicks']==0,status=r['status']);command('clear-duplicate')
    command('reset');r=runner.run(runner.start(doc,'headless')['id']);actual=state()
    add('native_headless_background_replay',r['status']=='completed' and actual['input']=='workflow 中文' and actual['clicks']==1,status=r['status'])
    add('audit_step_operation_links',all(x['operation_id'] in {e['operation_id']for e in client.runtime.store.query(kind='workflow.step_completed')}for x in runner.load(r['id'])['steps']))
    server,state_web,url=web_server('draft')
    try:
        web_policy={'apps':[],'paths':[str(args.output)],'origins':[url],'write':True,'trusted_host':True,'require_approval':False}
        for mode in ['headless','headed']:
            c=Client(Runtime(args.output/('web-'+mode),web_policy));c.open(apps=[])
            steps=[{'id':identifier(),'kind':'browser.open','arguments':{'url':url}}]
            for key,value in [('name','林安'),('project','Beacon'),('quantity','7'),('note','内部测试草稿')]:steps.append({'id':identifier(),'kind':'browser.act','arguments':{'action':'fill','selector':f'input[name={key}]','expected_url':url+'/','value':value}})
            steps.append({'id':identifier(),'kind':'browser.act','arguments':{'action':'click','selector':'button','expected_url':url+'/'}})
            output=args.output/(mode+'.txt');steps.append({'id':identifier(),'kind':'code.run','arguments':{'language':'python','code':f'from pathlib import Path\nPath({str(output)!r}).write_text("workflow-result")','cwd':str(args.output),'timeout':10}})
            webdoc=library.save({'schema':SCHEMA,'id':identifier(),'name':'Owned web and code','revision':1,'parent_sha256':None,'apps':{},'steps':steps})
            rr=RuntimeWorkflowRunner(c,args.output/'runs');result=rr.run(rr.start(webdoc,mode)['id']);obs=c.call('browser.observe')
            add('web_and_code_'+mode,result['status']=='completed' and state_web['draft']['quantity']=='7' and output.read_text()=='workflow-result' and obs['result']['headless']==(mode=='headless'),status=result['status'],browser_mode_verified=obs.get('result',{}).get('headless'))
            c.call('session.close')
    finally:server.shutdown();server.server_close();client.call('session.close')
    report['sources']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path('src/bokkio/runtime_workflow.py'),Path('src/bokkio/manual_recording.py'),Path('src/bokkio/workflow_studio.py'),Path('src/bokkio/native/macos_record.swift'),Path('fixtures/workflow-recording/main.swift')]}
    save_json(args.output/'report.json',report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    r=main(args);raise SystemExit(0 if r['passed']==r['total'] else 1)
