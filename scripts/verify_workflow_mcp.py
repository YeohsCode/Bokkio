"""Official MCP stdio workflow replay on the dedicated native lab fixture."""
from pathlib import Path
import argparse,asyncio,json,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bokkio.runtime_workflow import WorkflowLibrary
from bokkio.workflow import save_json
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main(args):
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    document=json.loads(args.workflow.read_text())
    if any(g['name']!='BokkioWorkflowLab' or g['path']!=str(args.fixture.resolve())for g in document['apps'].values()) or any(s['kind']!='native' or s['window']!='Bokkio Workflow Lab'for s in document['steps']):raise ValueError('Only the owned native lab workflow is accepted')
    doc=WorkflowLibrary(args.output/'workflows').save(document)
    policy={'apps':['BokkioWorkflowLab'],'launch_apps':doc['apps'],'workflows':[doc['id']],'write':True,'require_approval':False}
    save_json(args.output/'policy.json',policy)
    save_json(Path('/tmp/bokkio-workflow-fixture/command.json'),{'id':'mcp-reset-'+str(time.time_ns()),'action':'reset'})
    await asyncio.sleep(.2)
    params=StdioServerParameters(command=sys.executable,args=['-m','bokkio.runtime_cli','--state',str(args.output),'--policy',str(args.output/'policy.json'),'serve'])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as c:
            await c.initialize();tools=await c.list_tools()
            opened=(await c.call_tool('session.open',{'arguments':{'apps':[],'task_id':'workflow-mcp-owned'}})).structuredContent
            sid=opened['result']['session_id']
            call=lambda name,arguments:c.call_tool(name,{'session_id':sid,'arguments':arguments})
            r=(await call('workflow.run',{'workflow_id':doc['id'],'mode':args.mode})).structuredContent;rid=r['result']['run_id'];deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                result=(await call('workflow.status',{'run_id':rid})).structuredContent
                if result['result']['status'] in {'completed','failed','completion_unknown'}:break
                await asyncio.sleep(.2)
            actual=json.loads(Path('/tmp/bokkio-workflow-fixture/state.json').read_text())
            passed=result['result']['status']=='completed' and actual['input']=='workflow 中文' and actual['clicks']==1
            await call('session.close',{})
            report={'scope':'actual_official_MCP_owned_fixture_not_Harness_autonomous_business','passed':passed,'status':result['result']['status'],'tool_count':len(tools.tools),'workflow_tools':[t.name for t in tools.tools if t.name.startswith('workflow.')],'steps':result['result']['steps'],'independent_business_state_correct':actual['input']=='workflow 中文' and actual['clicks']==1}
            save_json(args.output/'report.json',report);print(json.dumps(report));return passed

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--workflow',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['headed','headless'],default='headed');p.add_argument('--approve-owned-fixture',action='store_true');args=p.parse_args()
    if not args.approve_owned_fixture:p.error('Explicit owned fixture authorization is required')
    raise SystemExit(0 if asyncio.run(main(args)) else 1)
