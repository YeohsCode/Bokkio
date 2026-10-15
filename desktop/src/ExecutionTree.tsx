import {useState} from 'react';
type Node={id:string;layer:number;title:string;engine:string;status:string;detail?:string;operation_id?:string;call_id?:string;dispatched?:boolean|string;reused_operation?:boolean;verification?:string;error?:string;events?:any[];children:Node[];counts?:{choices:number;operations:number;jev_calls?:number}};
const states:Record<string,string>={running:'进行中',ready:'准备中',pending:'待执行',paused:'已暂停',completed:'已结束',executed:'执行已返回',verified:'读回验证通过',queued:'已排队',returned:'已返回',failed:'失败',denied:'被拒绝',completion_unknown:'结果未知',cancelled:'已取消',cancelling:'停止中',skipped:'已停用',unlinked:'关联待确认',approval_required:'等待审批',waiting_approval:'等待审批',interrupted:'已中断'};
const kind:Record<number,string>={1:'任务 / 规划',2:'步骤 / 动作选择',3:'执行 / 验证'};
const bad=(s:string)=>['failed','denied','completion_unknown','interrupted'].includes(s);
export function ExecutionTree({trace}: {trace:Node}){
 const [expanded,setExpanded]=useState<Record<string,boolean>>({});
 const active=(n:Node)=>n.layer===1||['running','ready','queued','failed','denied','completion_unknown','paused'].includes(n.status);
 function render(n:Node){
  const open=expanded[n.id]??active(n),hasChildren=n.children.length>0;
  return <li role="treeitem" aria-level={n.layer} aria-expanded={hasChildren?open:undefined} className={'trace-node depth-'+n.layer} key={n.id} data-trace-id={n.id} data-layer={n.layer}>
   <div className="trace-row"><button className="trace-toggle" aria-expanded={open} aria-label={(open?'收起':'展开')+' '+n.title} disabled={!hasChildren&&!n.events?.length} onClick={()=>setExpanded(v=>({...v,[n.id]:!open}))}>{open?'▾':'▸'}</button><span className="trace-level">L{n.layer}</span><div className="trace-heading"><strong>{n.title}</strong><small>{kind[n.layer]} · {n.engine}</small></div><span className={'pill '+(bad(n.status)?'red':n.status==='verified'?'green':'')}>{states[n.status]||n.status}</span></div>
   {n.detail&&<div className="trace-detail">{n.detail}</div>}
   {n.verification&&<div className="trace-detail">完成检查：{({passed:'通过',failed:'失败',not_configured:'未配置',pending:'待核验'} as Record<string,string>)[n.verification]||n.verification}</div>}
   {n.layer===3&&<div className="trace-detail receipt"><code title={n.operation_id}>operation {n.operation_id?.slice(0,12)||'—'}</code>{n.dispatched!==undefined&&<span>{n.dispatched===true?'已派发':n.dispatched===false?'未派发写操作':'派发结果未知'}</span>}</div>}
   {n.reused_operation&&<p className="trace-detail">多个调用引用同一操作；不是重复派发。</p>}{n.error&&<p className="trace-detail trace-error">{n.error}</p>}
   {open&&n.events&&n.events.length>0&&<div className="trace-receipts">{n.events.map(e=><div className="trace-event" key={e.id}><time>{new Date(e.time*1000).toLocaleTimeString()}</time><code>{e.kind}</code><span>{e.status?(states[e.status]||e.status):''}</span>{typeof e.duration_ms==='number'&&<span>{Math.round(e.duration_ms)} ms</span>}{e.dispatched_this_attempt===false&&<span>本次未重发</span>}</div>)}</div>}
   {open&&hasChildren&&<ol role="group">{n.children.map(render)}</ol>}
   {open&&n.layer===2&&!hasChildren&&<p className="trace-detail">尚无执行回执。</p>}
  </li>
 }
 function visit(n:Node,open:boolean,out:Record<string,boolean>){out[n.id]=open||n.layer===1;n.children.forEach(c=>visit(c,open,out));return out}
 return <section className="execution-tree" aria-label="分层执行日志"><div className="trace-tools"><strong>分层实时日志</strong>{trace.counts&&<span className="tiny">{trace.counts.choices} 次工具选择 · {trace.counts.operations} 条执行记录 · {trace.counts.jev_calls||0} 次 Jev 请求</span>}<button onClick={()=>setExpanded(visit(trace,true,{}))}>全部展开</button><button onClick={()=>setExpanded(visit(trace,false,{}))}>收起明细</button></div><ol role="tree">{render(trace)}</ol></section>
}
