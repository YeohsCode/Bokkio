"""DeepSeek Harness SDK bridge; SDK owns its existing planning/execution loop."""
import json,os,sys,signal
from pathlib import Path

def emit(value):
    raw=json.dumps(value,ensure_ascii=False,default=lambda v:v.model_dump() if hasattr(v,'model_dump') else {'method':v.method,'payload':v.payload} if hasattr(v,'method') and hasattr(v,'payload') else str(v));secret=os.environ.get('BOKKIO_PROVIDER_KEY')
    if secret:raw=raw.replace(secret,'[redacted]')
    print(raw,flush=True)
def main():
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt()))
    config=json.load(sys.stdin)
    try:
        from deepseek_harness import DeepSeekHarness
        folder=Path(config['folder']);patch=folder/'harness.patch.yml'
        # JSON is YAML: write provider config without shell quoting or credentials.
        extension=[{'id':name,'disabled':True} for name in ('persistent-bash','persistent-pwsh','llm-deepseek','session-log-deepseek')]
        extension.append({'insert':[{'id':'bokkio-llm','name':'@deepseek-ai/dsh-llm-pi-ai','config':{'providers':{'bokkio':{'apiKeyEnv':'BOKKIO_PROVIDER_KEY','api':'openai-completions','baseURL':config['base_url'],'models':[{'id':config['model'],'input':['text'],'contextWindow':131072,'maxTokens':8192,'reasoningEfforts':{'low':'low'}}]}}}}, {'id':'bokkio-mcp','name':'@deepseek-ai/dsh-mcp-client','config':{'serverName':'bokkio','transport':'stdio','command':config['runtime_python'],'args':['-m','bokkio.runtime_cli','--state',config['state'],'--local','serve'],'cwd':config['runtime_cwd'],'failOnStartupError':True}}]})
        patch.write_text(json.dumps(extension));patch.chmod(0o600)
        instructions='Use Bokkio MCP for desktop, browser, files, code and saved workflows. This is the current user’s local desktop: execute the requested task directly. Observe the exact window named in the task with max_nodes=120 and max_bytes=100000. Open a session first; session_id and operation_id are top-level siblings of arguments. Observe the real target before actions, read back results, and never redispatch completion_unknown. Prefer a saved Workflow when it matches. Do not claim completion from a posted input receipt alone. Task: '+config['prompt']
        kwargs={}
        if sys.platform=='win32':
            import deepseek_harness_runtime
            executable=Path(deepseek_harness_runtime.__file__).parent/'runtime'/'deepseek-harness-sdk-runtime-win-x64.exe'
            if executable.is_file():kwargs['dsh_bin']=str(executable)
        with DeepSeekHarness(**kwargs,dsh_home=str(folder/'harness'),profile='sdk-minimal',provider='bokkio',model=config['model'],reasoning_effort='low',max_tokens=8192,cwd=config['workspace'],patches=(str(patch),),env={'BOKKIO_PROVIDER_KEY':os.environ['BOKKIO_PROVIDER_KEY'],'BOKKIO_DESKTOP_TASK_ID':config['task_id']},initialize_timeout_seconds=60,request_timeout_seconds=600) as harness:
            result=harness.run(instructions,session_id=config['task_id'],on_notification=lambda n:emit({'kind':'notification','data':n}))
            emit({'kind':'result','status':'completed' if result.finish_reason=='completed' else 'failed','response':result.final_response,'finish_reason':result.finish_reason})
    except KeyboardInterrupt:
        emit({'kind':'result','status':'cancelled','response':''})
    except Exception as error:
        message=str(error).replace(os.environ.get('BOKKIO_PROVIDER_KEY','__no_key__'),'[redacted]')
        emit({'kind':'result','status':'failed','error':message})
if __name__=='__main__':main()
