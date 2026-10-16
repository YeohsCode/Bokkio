import React,{useEffect,useState} from 'react';

type State=Record<string,any>;
const labels:Record<string,string>={checking:'检查连接中',preparing:'准备连接组件',connecting:'正在登录',awaiting_login:'等待微软确认',connected:'已连接',disconnected:'未连接',needs_setup:'需要准备组件',needs_login:'需要重新登录',failed:'连接失败',cancelled:'已取消',cancelling:'正在取消'};

export function OutlookSettings(){
 const [state,setState]=useState<State>({status:'checking'}),[error,setError]=useState(''),[count,setCount]=useState<State|null>(null),[querying,setQuerying]=useState(false);
 const busy=['checking','preparing','connecting','awaiting_login','cancelling'].includes(state.status);
 async function refresh(){try{setState(await window.bokkio.api('/api/outlook/status'))}catch(e:any){setError(e.message)}}
 useEffect(()=>{refresh();const id=setInterval(refresh,1500);return()=>clearInterval(id)},[]);
 async function action(action:string){setError('');setCount(null);try{setState(await window.bokkio.api('/api/outlook/action',{action}))}catch(e:any){setError(e.message)}}
 async function unread(){
  const now=new Date(),start=new Date(now);start.setHours(0,0,0,0);start.setDate(start.getDate()-(start.getDay()+6)%7);
  setQuerying(true);setError('');try{setCount(await window.bokkio.api('/api/outlook/unread',{start:start.toISOString(),end:now.toISOString()}))}catch(e:any){setError(e.message)}finally{setQuerying(false)}
 }
 return <div className="settings-card outlook-settings">
  <h3>Microsoft / Outlook 账户</h3>
  <p className="hint">使用微软官方 Graph PowerShell 登录。密码只在微软页面输入；登录状态由微软 SDK 缓存并自动续期。同一电脑首次登录后可跨应用重启使用。</p>
  <div className="status-row"><span>连接状态</span><strong role="status" aria-label="Outlook 连接状态">{labels[state.status]||state.status}</strong></div>
  {state.account&&<div className="status-row"><span>微软账户</span><span>{state.account}</span></div>}
  {state.module_version&&<p className="tiny">Graph Authentication {state.module_version} · PowerShell {state.powershell_version}</p>}
  {state.message&&<p className="hint">{state.message}</p>}
  {state.status==='awaiting_login'&&<div className="outlook-challenge"><p>打开微软登录页，输入以下设备码，再登录并确认授权。</p><code aria-label="微软设备码">{state.code}</code><button onClick={()=>window.bokkio.openMicrosoftLogin()}>打开微软登录页</button></div>}
  {error&&<p role="alert">{error.replace(/^Error invoking remote method '[^']+': (?:Error: )?/,'')}</p>}
  <div className="row">
   {state.status==='needs_setup'?<button disabled={busy} onClick={()=>action('prepare')}>准备 Outlook 组件</button>:<button disabled={busy||querying} onClick={()=>action('connect')}>{state.status==='connected'?'验证登录':'连接 Outlook'}</button>}
   {state.account&&<button disabled={busy||querying} onClick={()=>action('disconnect')}>退出 Graph 登录</button>}
   {busy&&state.status!=='checking'&&<button onClick={async()=>setState(await window.bokkio.api('/api/outlook/cancel',{}))}>取消连接</button>}
   <button disabled={busy||querying||state.status!=='connected'} onClick={unread}>{querying?'正在统计…':'统计本周未读邮件'}</button>
  </div>
  {count&&<p className="notice" role="status">收件箱本周收到、目前仍未读：<strong>{count.count}</strong> 封。按本机时区从周一零点统计至查询时刻。</p>}
  <p className="hint">当前连接只申请读取邮件基本属性。退出会清除此系统用户的 Graph PowerShell 登录缓存；不退出 Outlook 应用。微软要求重新验证时，这里会显示“需要重新登录”。</p>
 </div>
}
