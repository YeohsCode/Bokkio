"""DeepSeek Harness SDK bridge; SDK owns its existing planning/execution loop."""
import json,os,sys,signal
from pathlib import Path

def emit(value):
    raw=json.dumps(value,ensure_ascii=False,default=lambda v:v.model_dump() if hasattr(v,'model_dump') else {'method':v.method,'payload':v.payload} if hasattr(v,'method') and hasattr(v,'payload') else str(v))
    for field in ('BOKKIO_PROVIDER_KEY','BOKKIO_JEV_API_KEY'):
        if secret:=os.environ.get(field):raw=raw.replace(secret,'[redacted]')
    print(raw,flush=True)
def mcp_arguments(config):
    return ['-m','bokkio.desktop_decision','--state',config['state']] if config.get('jev_enabled',True) else ['-m','bokkio.runtime_cli','--state',config['state'],'--local','serve']

def mcp_environment_keys(jev_enabled=True):
    return ['BOKKIO_DESKTOP_TASK_ID']+(['BOKKIO_JEV_API_KEY','BOKKIO_JEV_SOURCE','BOKKIO_JEV_MODEL','BOKKIO_JEV_API_URL','BOKKIO_JEV_CONFIG','BOKKIO_PROVIDER_KEY','BOKKIO_PROVIDER_BASE_URL','OPENROUTER_API_KEY','TYPESAFE_API_KEY'] if jev_enabled else [])

def patch_yaml(extension,jev_enabled=True):
    # SDK subprocesses scrub ambient credentials. Explicit !!js env references preserve keys without writing their values.
    keys=mcp_environment_keys(jev_enabled)
    expression='Object.fromEntries('+json.dumps(keys)+'.filter(key => process.env[key] !== undefined).map(key => [key, process.env[key]]))'
    return json.dumps(extension).replace('"__BOKKIO_MCP_ENV__"',"!!js '"+expression+"'")

def instructions_for(prompt,jev_enabled=True):
    mode=JEV_INSTRUCTIONS if jev_enabled else 'Jev is disabled for this task. You own global planning and native action/target selection. Use desktop.observe and the returned refs/observation_id with desktop.act, desktop.input or desktop.pixel; do not call desktop.step. Read back each action before continuing. expected_value is only valid for type; omit it for set_value. Once the readback matches the requested literal, report success without rewriting it. '
    return mode+GENERAL_INSTRUCTIONS+prompt

JEV_INSTRUCTIONS='You are the global planner. For every new native UI interaction, call desktop.step with one local goal, app, exact window and allowed_values. Jev selects the action and target; do not choose refs yourself or use code/process tools to manipulate UI. For keys, right-click, drag or explicit foreground input, pass the input specification to desktop.step; Jev chooses its native target. Each step executes at most one action and returns readback; use that evidence to continue or replan. Saved workflows execute their fixed steps without Jev. Code/process tools are for non-UI work such as files and data. Never silently bypass a failed Jev decision. '
GENERAL_INSTRUCTIONS='Use Bokkio MCP for desktop, browser, files, code and saved workflows. This is the current user’s local desktop: execute the requested task directly. Observe the exact window named in the task with max_nodes=60 and max_bytes=16000. Open a session first; session_id and operation_id are top-level siblings of arguments. Observe the real target before actions, read back results, and never redispatch completion_unknown. Prefer a saved Workflow when it matches. Do not claim completion from a posted input receipt alone. Task: '

def harness_result(result):
    response=result.final_response or ''
    completed=result.finish_reason=='completed' and bool(response.strip())
    return {'kind':'result','status':'completed' if completed else 'failed','response':response,'finish_reason':result.finish_reason,
            **({'error':'Harness ended without a visible final answer; inspect execution receipts before retrying.'} if not response.strip() else {})}

def main():
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    config=json.load(sys.stdin)
    try:
        from deepseek_harness import DeepSeekHarness
        folder=Path(config['folder']);patch=folder/'harness.patch.yml'
        # JSON is YAML: write provider config without shell quoting or credentials.
        extension=[{'id':name,'disabled':True} for name in ('persistent-bash','persistent-pwsh','llm-deepseek','session-log-deepseek')]
        extension.append({'insert':[{'id':'bokkio-llm','name':'@deepseek-ai/dsh-llm-pi-ai','config':{'providers':{'bokkio':{'apiKeyEnv':'BOKKIO_PROVIDER_KEY','api':'openai-completions','baseURL':config['base_url'],'models':[{'id':config['model'],'input':['text'],'contextWindow':131072,'maxTokens':8192,'reasoningEfforts':{'low':'low'}}]}}}}, {'id':'bokkio-mcp','name':'@deepseek-ai/dsh-mcp-client','config':{'serverName':'bokkio','transport':'stdio','command':config['runtime_python'],'args':mcp_arguments(config),'env':'__BOKKIO_MCP_ENV__','cwd':config['runtime_cwd'],'failOnStartupError':True}}]})
        patch.write_text(patch_yaml(extension,config.get('jev_enabled',True)));patch.chmod(0o600)
        instructions=instructions_for(config['prompt'],config.get('jev_enabled',True))
        kwargs={}
        if sys.platform=='win32':
            import deepseek_harness_runtime
            executable=Path(deepseek_harness_runtime.__file__).parent/'runtime'/'deepseek-harness-sdk-runtime-win-x64.exe'
            if executable.is_file():kwargs['dsh_bin']=str(executable)
        with DeepSeekHarness(**kwargs,dsh_home=str(folder/'harness'),profile='sdk-minimal',provider='bokkio',model=config['model'],reasoning_effort='low',max_tokens=8192,cwd=config['workspace'],patches=(str(patch),),env={'BOKKIO_PROVIDER_KEY':os.environ['BOKKIO_PROVIDER_KEY'],'BOKKIO_DESKTOP_TASK_ID':config['task_id'],**{k:v for k,v in os.environ.items() if k.startswith('BOKKIO_JEV_')},'BOKKIO_PROVIDER_BASE_URL':config['base_url']},initialize_timeout_seconds=60,request_timeout_seconds=600) as harness:
            result=harness.run(instructions,session_id=config['task_id'],on_notification=lambda n:emit({'kind':'notification','data':n}))
            emit(harness_result(result))
    except KeyboardInterrupt:
        emit({'kind':'result','status':'cancelled','response':''})
    except Exception as error:
        message=str(error).replace(os.environ.get('BOKKIO_PROVIDER_KEY','__no_key__'),'[redacted]')
        emit({'kind':'result','status':'failed','error':message})
if __name__=='__main__':main()
