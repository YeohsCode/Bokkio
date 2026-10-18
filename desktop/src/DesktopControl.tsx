import React,{useEffect,useState} from 'react';

type State=Record<string,any>;
const labels:Record<string,string>={disabled:'用户接管未开启',ready:'等待用户接管',paused_by_user:'桌面操作已暂停',unavailable:'接管监听不可用，桌面操作已暂停'};

export function DesktopControl({compact=false}:{compact?:boolean}){
 const [state,setState]=useState<State>({state:'loading'}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function refresh(){try{setState(await window.bokkio.api('/api/control'))}catch(e:any){setError(e.message)}}
 useEffect(()=>{refresh();const timer=setInterval(refresh,500);return()=>clearInterval(timer)},[]);
 async function action(action:string){setBusy(true);setError('');try{setState(await window.bokkio.api('/api/control',{action}))}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 const paused=state.enabled&&state.state!=='ready';
 if(compact)return <div className="row" role="status"><span>{labels[state.state]||'检查接管状态'}</span>{paused&&<button disabled={busy||!state.healthy||!!state.error} onClick={()=>action('resume')}>继续桌面操作</button>}{error&&<span role="alert">{error}</span>}</div>;
 return <div className="settings-card">
  <h3>用户接管</h3>
  <label className="app-choice"><input type="checkbox" checked={!!state.enabled} disabled={busy||state.state==='loading'} onChange={e=>action(e.target.checked?'enable':'disable')}/>用户操作键盘或鼠标时暂停桌面操作</label>
  <p className="hint">不记录输入文字。暂停后先松开按键和鼠标，再点击继续；任务需要重新读取目标。已暂停的 Workflow 请从原运行记录继续。已发出的原生调用不能撤回。</p>
  <p role="status">{labels[state.state]||'检查接管状态'}</p>
  {state.error&&<p role="alert">{state.error}</p>}
  {paused&&<button disabled={busy||!state.healthy||!!state.error} onClick={()=>action('resume')}>继续桌面操作</button>}
  {state.enabled&&state.state==='unavailable'&&<button disabled={busy} onClick={()=>action('enable')}>重新启动监听</button>}
  {state.enabled&&state.platform==='darwin'&&<button onClick={()=>window.bokkio.openPermissions('input')}>输入监控设置</button>}
  {error&&<p role="alert">{error.replace(/^Error invoking remote method '[^']+': (?:Error: )?/,'')}</p>}
 </div>
}
