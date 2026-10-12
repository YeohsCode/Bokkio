"""Run installed Codex/Hermes/DeepSeek clients against owned Bokkio MCP fixtures.

Provider credentials are resolved in memory from Hermes, never written to reports.
Use a private output directory. The independent fixture controller approves only
one native literal and one exact code hash; it is not customer human approval.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from bokkio.runtime import Runtime


def glm_config(hermes_python, home):
    code = "import yaml,json,sys;from pathlib import Path;c=yaml.safe_load((Path(sys.argv[1])/'config.yaml').read_text());print(json.dumps(c['model']))"
    result = subprocess.run([str(hermes_python), '-c', code, str(home)], capture_output=True, text=True, check=True)
    model = json.loads(result.stdout)
    if model.get('default') != 'z-ai/glm-5.3-flash' or model.get('base_url') != 'https://openrouter.ai/api/v1':
        raise ValueError('Configured Hermes model/endpoint differs from the authorized GLM 5.3 Flash route')
    if not isinstance(model.get('api_key'), str) or not model['api_key'].startswith('sk-or-'):
        raise ValueError('Expected an existing configured OpenRouter credential; no key printed')
    return model


def delegated_code(pid, token):
    """A bounded native transaction chosen by the caller, not a Core app adapter."""
    return f'''from pathlib import Path
import time
from bokkio.sdk import Client
c=Client.from_environment()
obs_args={{'app':'{pid}','window':'Bokkio Runtime Contract','max_nodes':100}}
obs=c.call('desktop.observe',obs_args)
assert obs['status']=='completed', obs
node=next(n for n in obs['result']['nodes'] if n['role']=='text_field' and n.get('name')=='Search')
args={{'app':'{pid}','window':'Bokkio Runtime Contract','observation_id':obs['result']['observation_id'],'action':'set_value','ref':node['ref'],'value':'{token}'}}
op='native-{token}'
action=c.call('desktop.act',args,operation_id=op)
assert action['status']=='approval_required', action
deadline=time.monotonic()+5
while time.monotonic()<deadline:
    approval=c.call('approval.status',{{'approval_id':action['approval_id']}})
    if approval['result'][0]['status']=='approved':break
    time.sleep(.05)
else:raise TimeoutError('Independent native approval not received')
action=c.call('desktop.act',args,operation_id=op)
assert action['status']=='verified', action
obs=c.call('desktop.observe',obs_args)
assert any(n['role']=='text_field' and n.get('name')=='Search' and n.get('value')=='{token}' for n in obs['result']['nodes']), obs
Path('result.csv').write_text('kind,value\\nfixture,{token}\\n',encoding='utf-8')
print('native readback verified; csv created')
'''


def prepare(root, client, pid, strategy='native'):
    folder = root / client; folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    work = folder / 'workspace'; work.mkdir(exist_ok=True, mode=0o700)
    token = 'HARNESS-' + client.upper() + '-1'
    code = "from pathlib import Path\nPath('result.csv').write_text('kind,value\\nfixture," + token + "\\n',encoding='utf-8')\nprint('csv created')\n"
    if strategy=='sdk-code':code=delegated_code(pid,token)
    policy = {'apps':[str(pid)],'paths':[str(work)],'write':True,'trusted_host':True,'require_approval':True}
    policy_file = folder/'policy.json'; policy_file.write_text(json.dumps(policy))
    runtime = Runtime(folder/'state',policy)
    prompt = f'''Use ONLY the Bokkio MCP tools available in this client, not shell, file, browser or other tools.
This is an explicitly authorized disposable native/code integration test. An independent local fixture administrator reviews and approves only the requested literal and exact code below. You cannot approve requests yourself.
1. Call capabilities, then session.open with task_id="harness-{client}". The allowed app is "{pid}".
2. Observe app "{pid}", exact window "Bokkio Runtime Contract", max_nodes=100. Find the actual Search text_field ref.
3. Use desktop.act set_value to write exactly "{token}" with that observation_id and a unique operation_id. It must initially return approval_required. Poll approval.status, then retry with the SAME tool, arguments and operation_id after approved. If explicitly zero-dispatch stale rejection occurs, re-observe and use a new operation_id; never repeat completion_unknown.
4. Re-observe and confirm Search's value. Use code.run to execute the EXACT Python string below, cwd="{work}", language="python", timeout=30, output_limit=4096. Handle independent approval in the same way. Poll job.get until completed.
5. evidence.check path="{work}/result.csv", csv_rows=1, csv_columns=["kind","value"]. artifact.read the returned artifact. Call audit.query with limit=15 and metrics.summary to inspect the trace.
All calls after session.open must include its session_id. Raw MCP names may be sanitized by the client; use the published tools by their descriptions. Keep the session open for the independent judge. Finish with JSON containing session_id, native_value, csv_sha256, and status.
Exact code argument (JSON-encoded string): {json.dumps(code)}
'''
    if strategy=='sdk-code':
        prompt=f'''Use ONLY Bokkio MCP tools. This is an authorized disposable integration test with independent exact-request fixture admin approval. You cannot approve anything yourself.
Call capabilities, then session.open task_id="harness-{client}". All subsequent calls include session_id.
Execute the EXACT Python code below using code.run, cwd="{work}", language="python", timeout=30, output_limit=4096 and a unique operation_id. The generated code uses the delegated Bokkio SDK to observe and write the actual native Search field and create CSV. The administrator independently approves the code and its native write. Code execution is trusted-host, not an OS sandbox.
The first code.run returns approval_required. Call approval.status; once approved retry the EXACT same code.run arguments and operation_id. Then job.get until completed. Never replay completion_unknown.
After job completes, call evidence.check path="{work}/result.csv", csv_rows=1, csv_columns=["kind","value"]; artifact.read its artifact. Call audit.query limit=15 and metrics.summary. Finish with JSON containing session_id and status. Leave session open for independent judge.
Exact code argument (JSON-encoded string): {json.dumps(code)}
'''
    prompt += '\nMCP call envelope: business fields go inside arguments; session_id and operation_id are top-level siblings, NOT inside arguments. Example: '+json.dumps({'session_id':'REPLACE_WITH_OPENED_SESSION_ID','operation_id':'code-'+client,'arguments':{'code':code,'cwd':str(work),'language':'python','timeout':30,'output_limit':4096}})+'\nIf a call omits session_id or arguments, fix that exact schema error. Never repeat an unchanged denied call.\n'
    (folder/'prompt.txt').write_text(prompt)
    return folder,work,token,code,policy_file,runtime


def approve_loop(runtime,pid,token,code,work,stop,decisions):
    while not stop.wait(.05):
        with runtime.store.connect() as db:
            rows = db.execute("SELECT a.id,a.status,o.tool,o.request,o.session_id FROM approvals a JOIN operations o ON o.id=a.operation_id WHERE a.status='pending'").fetchall()
        for row in rows:
            args = json.loads(row['request']); allowed=False
            if row['tool']=='desktop.act':
                allowed = args.get('action')=='set_value' and str(args.get('app'))==str(pid) and args.get('window')=='Bokkio Runtime Contract' and args.get('value')==token
                with runtime.store.connect() as db:
                    observed=db.execute('SELECT payload FROM observations WHERE id=? AND session_id=?',(args.get('observation_id'),row['session_id'])).fetchone()
                if observed:
                    from bokkio.selector import flatten
                    nodes=list(flatten(json.loads(observed[0])['snapshot']['windows']))
                    allowed=allowed and any(n['ref']==args.get('ref') and n['role']=='text_field' and n.get('name')=='Search' for n in nodes)
                else:allowed=False
            elif row['tool']=='code.run':
                allowed = args.get('code')==code and Path(args.get('cwd','')).resolve()==work.resolve() and args.get('language','python')=='python' and args.get('timeout',30)<=30
            try:
                runtime.store.decide(row['id'],'approved' if allowed else 'denied','Independent exact-request disposable Harness acceptance controller')
                decisions.append({'tool':row['tool'],'decision':'approved' if allowed else 'denied'})
            except ValueError:
                pass


def launch(command,env,folder,budget):
    with (folder/'client.stdout').open('w') as out,(folder/'client.stderr').open('w') as err:
        process=subprocess.Popen(command,env=env,cwd=folder/'workspace',stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
        try:
            return process.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            return 124


def dsh_script(folder,python,project_python,policy,state,work):
    patch=folder/'dsh.patch.yml'
    server_args=['-m','bokkio.runtime_cli','--state',str(state),'--policy',str(policy),'serve']
    patch.write_text(f'''- id: persistent-bash
  disabled: true
- id: persistent-pwsh
  disabled: true
- id: llm-deepseek
  disabled: true
- id: session-log-deepseek
  disabled: true
- insert:
    - id: bokkio-llm
      name: '@deepseek-ai/dsh-llm-pi-ai'
      config:
        providers:
          bokkio-glm:
            apiKeyEnv: BOKKIO_GLM_KEY
            api: openai-completions
            baseURL: https://openrouter.ai/api/v1
            retryPolicy:
              mode: normal
              maxRetries: 1
            models:
              - id: z-ai/glm-5.3-flash
                input: [text]
                contextWindow: 1048576
                maxTokens: 4096
                reasoningEfforts: {{low: low}}
    - id: bokkio-mcp
      name: '@deepseek-ai/dsh-mcp-client'
      config:
        serverName: bokkio
        transport: stdio
        command: {json.dumps(str(project_python))}
        args: {json.dumps(server_args)}
        cwd: {json.dumps(str(work))}
        failOnStartupError: true
''')
    script=folder/'run_dsh.py'
    script.write_text('''from pathlib import Path
import os,json
from deepseek_harness import DeepSeekHarness
folder=Path(__file__).parent
with DeepSeekHarness(dsh_home=str(folder/'dsh-home'),profile='sdk-minimal',provider='bokkio-glm',model='z-ai/glm-5.3-flash',reasoning_effort='low',max_tokens=4096,cwd=str(folder/'workspace'),patches=(str(folder/'dsh.patch.yml'),),env={'BOKKIO_GLM_KEY':os.environ['BOKKIO_GLM_KEY']},initialize_timeout_seconds=60,request_timeout_seconds=240) as harness:
 result=harness.run((folder/'prompt.txt').read_text(),session_id='bokkio-development-1')
 (folder/'dsh-result.json').write_text(json.dumps({'final':result.final_response,'finish_reason':result.finish_reason,'events':result.events,'notifications':result.notifications},default=str))
 print(result.final_response)
 raise SystemExit(0 if result.finish_reason=='completed' and result.final_response else 1)
''')
    return [str(python),str(script)]


def run(args):
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    model=glm_config(args.hermes_python,args.hermes_home)
    fixture_data=args.output/'fixture.json'
    fixture=subprocess.Popen([str(args.fixture.resolve())],env={**os.environ,'BOKKIO_NATIVE_RESULT':str(fixture_data)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    deadline=time.monotonic()+10
    while not fixture_data.exists() and time.monotonic()<deadline:time.sleep(.05)
    if not fixture_data.exists():raise RuntimeError('Owned fixture startup failed')
    reports=[]
    try:
        for client in args.clients:
            folder,work,token,code,policy,runtime=prepare(args.output,client,fixture.pid,args.strategy)
            env=os.environ.copy()
            if client=='codex-current':
                cmd=None
                label='current_Codex_conversation'
            elif client=='codex':
                mcp={'bokkio':{'command':str(Path(sys.executable).absolute()),'args':['-m','bokkio.runtime_cli','--state',str(folder/'state'),'--policy',str(policy),'serve'],'cwd':str(work)}}
                # Inline JSON objects are also TOML-compatible through explicit inline-table encoding.
                table='{bokkio={command='+json.dumps(mcp['bokkio']['command'])+',args='+json.dumps(mcp['bokkio']['args'])+',cwd='+json.dumps(str(work))+'}}'
                cmd=[str(args.codex),'exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','-s','read-only','-m','gpt-6.1-sol','-c','model_reasoning_effort="low"','-c','mcp_servers='+table,'--json',(folder/'prompt.txt').read_text()]
                label='gpt-6.1-sol'
            elif client=='hermes':
                home=folder/'profiles'/'acceptance';home.mkdir(parents=True,mode=0o700)
                config={'model':{k:v for k,v in model.items() if k!='api_key'},'toolsets':['bokkio'],'agent':{'max_turns':24,'api_max_retries':1},'mcp_servers':{'bokkio':{'command':str(Path(sys.executable).absolute()),'args':['-m','bokkio.runtime_cli','--state',str(folder/'state'),'--policy',str(policy),'serve'],'enabled':True}},'checkpoints':{'enabled':False}}
                # JSON is valid YAML; credential is injected only into child env.
                cfg=home/'config.yaml';cfg.write_text(json.dumps(config));cfg.chmod(0o600)
                env['HERMES_HOME']=str(home)
                env['OPENROUTER_API_KEY']=model['api_key']
                cmd=[str(args.hermes),'chat','--query-file',str(folder/'prompt.txt'),'--oneshot','--ignore-rules','-t','bokkio','--max-turns','24','--run-budget',str(args.budget),'--format','stream-json','--reasoning','none']
                label=model['default']
            else:
                env['BOKKIO_GLM_KEY']=model['api_key']
                cmd=dsh_script(folder,args.dsh_python,Path(sys.executable).absolute(),policy,folder/'state',work)
                label=model['default']
            stop=threading.Event();decisions=[]
            controller=threading.Thread(target=approve_loop,args=(runtime,fixture.pid,token,code,work,stop,decisions),daemon=True);controller.start()
            started=time.monotonic()
            try:
                if cmd is None:
                    (folder/'ready.json').write_text(json.dumps({'pid':fixture.pid,'folder':str(folder),'strategy':args.strategy}))
                    deadline=time.monotonic()+args.budget
                    while not (folder/'complete.json').exists() and time.monotonic()<deadline:time.sleep(.1)
                    exit_code=0 if (folder/'complete.json').exists() else 124
                else:exit_code=launch(cmd,env,folder,args.budget+30)
            finally:stop.set();controller.join(timeout=5)
            actual=json.loads(fixture_data.read_text())['input']
            csv_file=work/'result.csv';rows=[]
            if csv_file.exists():
                with csv_file.open(encoding='utf-8',newline='') as file:rows=list(csv.DictReader(file))
            with runtime.store.connect() as db:
                ops=[dict(row) for row in db.execute('SELECT tool,status FROM operations')]
                kinds=[row[0] for row in db.execute('SELECT kind FROM events')]
                sessions=[row[0] for row in db.execute('SELECT id FROM sessions')]
                approval_states=[row[0] for row in db.execute('SELECT status FROM approvals')]
                has_jobs=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'").fetchone()
                job_states=[row[0] for row in db.execute('SELECT status FROM jobs')] if has_jobs else []
                parent_links=sum(bool(json.loads(row[0]).get('parent_operation')) for row in db.execute("SELECT data FROM events WHERE kind='request.received'"))
            required={'capabilities','session.open','desktop.observe','desktop.act','code.run','job.get','evidence.check','artifact.read','audit.query','metrics.summary'}
            observed={o['tool'] for o in ops}
            native=actual==token;file_ok=rows==[{'kind':'fixture','value':token}]
            approved={'desktop.act','code.run'}<={d['tool'] for d in decisions if d['decision']=='approved'}
            fully_executed=approval_states.count('consumed')>=2 and 'completed' in job_states
            if args.strategy=='sdk-code':fully_executed=fully_executed and parent_links>0
            record={'client':client,'model':label,'exit_code':exit_code,'duration_seconds':round(time.monotonic()-started,3),
                    'native_independent_readback':native,'csv_independent_check':file_ok,'approval_controller':approved,
                    'tool_coverage':sorted(observed),'missing_tools':sorted(required-observed),'audit_kinds':sorted(set(kinds)),
                    'passed':exit_code==0 and native and file_ok and approved and fully_executed and required<=observed,
                    'approval_states':approval_states,'job_states':job_states,'generated_code_parent_links':parent_links,
                    'approval_mode':'independent_exact_request_automated_fixture_admin','credential_exported':False,
                    'native_channel':'generated_code_delegated_sdk' if args.strategy=='sdk-code' else 'direct_mcp',
                    'caller_transport':'current_agent_official_stdio_client_bridge' if client=='codex-current' else 'installed_harness_mcp_stdio'}
            reports.append(record);print(json.dumps(record,ensure_ascii=False),flush=True)
            for session in sessions:runtime.call('session.close',session_id=session)
            (args.output/'report.json').write_text(json.dumps({'scope':'real_installed_harnesses_owned_fixture','results':reports},ensure_ascii=False,indent=2))
    finally:
        if fixture.poll() is None:fixture.terminate()
        fixture.wait(timeout=5)
    return reports


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--fixture',type=Path,required=True)
    parser.add_argument('--clients',nargs='+',choices=['codex','codex-current','hermes','deepseek'],default=['codex-current','hermes','deepseek'])
    parser.add_argument('--strategy',choices=['native','sdk-code'],default='native')
    parser.add_argument('--approve-owned-fixture',action='store_true',help='Explicitly enable exact-request fixture admin controller; not customer human approval')
    parser.add_argument('--codex',type=Path,default=Path('/Applications/Codex.app/Contents/Resources/codex'))
    parser.add_argument('--hermes',type=Path,default=Path.home()/'.local/bin/hermes')
    parser.add_argument('--hermes-python',type=Path,default=Path.home()/'.hermes/hermes-agent/venv/bin/python')
    parser.add_argument('--hermes-home',type=Path,default=Path.home()/'.hermes')
    parser.add_argument('--dsh-python',type=Path,required=True);parser.add_argument('--budget',type=int,default=240)
    args=parser.parse_args()
    if not args.approve_owned_fixture:parser.error('Disposable tests require explicit --approve-owned-fixture; no customer approval is implied')
    reports=run(args);raise SystemExit(0 if all(r['passed'] for r in reports) else 1)
