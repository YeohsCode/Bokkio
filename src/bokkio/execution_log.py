"""Project public SDK choices and Runtime receipts into a causal three-level log.

No hidden reasoning is inferred. Jev participation is derived from actual decision events.
"""
from __future__ import annotations
import json
from .audit import AuditStore

def architecture(jev_enabled=True):
    return {
        'planning': 'Harness SDK',
        'selection': 'Jev · native UI / Harness · orchestration' if jev_enabled else 'Harness SDK',
        'execution': 'Bokkio Runtime / Driver', 'jev_enabled': jev_enabled, 'jev_active': False,
        'legacy_three_layer': 'CLI: Planner → Jev → Driver',
    }

ARCHITECTURE = architecture()

def sdk_event(record):
    data=record.get('data',{})
    payload=data.get('payload',{}) if isinstance(data,dict) else {}
    event=payload.get('event',{}) if isinstance(payload,dict) else {}
    return event if isinstance(event,dict) else {}

def receipt(value):
    """Read structured MCP envelopes; never parse prose or string reprs."""
    if isinstance(value,str):
        if not value.lstrip().startswith(('{','[')):return None
        try:value=json.loads(value)
        except (ValueError,TypeError):return None
    if isinstance(value,list):
        return next((r for item in value if (r:=receipt(item))),None)
    if not isinstance(value,dict):return None
    if isinstance(value.get('operation_id'),str) and isinstance(value.get('status'),str):return value
    for key in ('structuredContent','content','text','message','data'):
        if key in value:
            found=receipt(value[key])
            if found:return found
    return None

def tool_name(name):
    from .runtime import TOOLS
    tools=TOOLS | {'desktop.step'}
    name=name if isinstance(name,str) else '未知工具'
    return next((tool for tool in sorted(tools,key=len,reverse=True) if '__'+tool.replace('.','_')+'_' in name),name)

def ingest_choice(job,record):
    event=sdk_event(record);data=event.get('data',{})
    if not isinstance(data,dict):return
    if event.get('type')=='tool/call':
        cid=data.get('callId')
        if not isinstance(cid,str):return
        choices=job.setdefault('choices',{})
        choice=choices.setdefault(cid,{'id':cid})
        args=data.get('arguments',{})
        if isinstance(args,str):
            try:args=json.loads(args)
            except ValueError:args={}
        args=args if isinstance(args,dict) else {}
        business=args.get('arguments',{});business=business if isinstance(business,dict) else {}
        choice.update(tool=tool_name(data.get('name','')),time=event.get('time'),
                      detail=' · '.join(str(business[k])[:160] for k in ('app','window','action') if business.get(k) is not None))
        if isinstance(args.get('operation_id'),str):choice['operation_id']=args['operation_id']
    elif event.get('type')=='tool/result':
        message=data.get('message',{});message=message if isinstance(message,dict) else {};source=message.get('source',{});source=source if isinstance(source,dict) else {}
        cid=source.get('callId') or data.get('callId')
        if not isinstance(cid,str):return
        choice=job.setdefault('choices',{}).setdefault(cid,{'id':cid})
        r=receipt(message)
        if r:choice.update(operation_id=r['operation_id'],returned_status=r['status'])
        else:choice['returned_status']='failed' if data.get('isError') or message.get('isError') else 'returned'


def operations(store,*,task_id=None,session_id=None):
    """Join by recorded session/task and operation IDs, never by elapsed proximity."""
    with store.connect() as db:
        if task_id:
            where="json_extract(s.policy,'$.task_id')=? OR EXISTS (SELECT 1 FROM events x WHERE x.operation_id=o.id AND json_extract(x.data,'$.task_id')=?)"
            args=(task_id,task_id)
        else:where='o.session_id=?';args=(session_id,)
        rows=db.execute('SELECT o.* FROM operations o LEFT JOIN sessions s ON s.id=o.session_id WHERE '+where+' ORDER BY o.created,o.id',args).fetchall()
        events=db.execute('SELECT e.* FROM events e JOIN operations o ON o.id=e.operation_id LEFT JOIN sessions s ON s.id=o.session_id WHERE '+where+' ORDER BY e.seq',args).fetchall()
    result={}
    for row in rows:
        raw=json.loads(row['result']) if row['result'] else {};request=json.loads(row['request']);request=request if isinstance(request,dict) else {}
        result[row['id']]={'id':'operation:'+row['id'],'layer':3,'title':row['tool'],'engine':'Bokkio Runtime / Driver','status':row['status'],
                          'operation_id':row['id'],'time':row['created'],'dispatched':raw.get('dispatched'),
                          'detail':' · '.join(str(request[k])[:160] for k in ('app','window','action') if request.get(k) is not None),
                          'error':raw.get('error'),'events':[],'children':[]}
    for row in events:
        node=result[row['operation_id']];data=json.loads(row['data'])
        if row['kind']=='request.received':node['parent_operation']=data.get('parent_operation');node['workflow_step']=data.get('workflow_step')
        if row['kind'].startswith('decision.'):
            node.setdefault('decision_events',[]).append({'kind':row['kind'],'time':row['time'],**{k:data[k] for k in ('engine','model','source','action','ref','confidence','duration_ms') if k in data}})
        node['events'].append({'id':row['event_id'],'time':row['time'],'kind':row['kind'],**{k:data[k] for k in ('status','dispatched','dispatched_this_attempt','duration_ms','error_type','job_id') if k in data}})
    return result


def chat_trace(job,state):
    root={'id':'chat:'+job['id'],'layer':1,'title':job['prompt'],'engine':'Harness SDK','status':job['status'],
          'detail':'Harness 规划任务；原生 UI 动作交给 Jev 选择，再由 Runtime 执行。','architecture':{**job.get('architecture',ARCHITECTURE),'jev_active':False},'children':[]}
    if root['architecture'].get('jev_enabled') is False:
        root['detail']='本任务已关闭 Jev；Harness 规划并选择动作，Runtime 执行和读回。'
    choices=job.get('choices')
    if choices is None:
        parsed={}
        for event in job.get('events',[]):ingest_choice(parsed,event)
        choices=parsed.get('choices',{})
    owners={};nodes={}
    unreturned='running' if job['status'] in {'running','cancelling'} else 'cancelled' if job['status']=='cancelled' else 'interrupted'
    for cid,choice in choices.items():
        node={'id':'choice:'+cid,'layer':2,'title':choice.get('tool','工具返回'),'engine':'Harness · 动作选择' if choice.get('tool') in {'desktop.act','desktop.input','desktop.pixel'} else 'Harness · 工具编排','status':choice.get('returned_status',unreturned),
              'detail':choice.get('detail',''),'call_id':cid,'children':[]};nodes[cid]=node
        if choice.get('tool')!='desktop.step':root['children'].append(node)
        if choice.get('operation_id'):owners.setdefault(choice['operation_id'],[]).append(node)
    audit=operations(AuditStore(state),task_id=job['id'])
    steps={oid:node for oid,node in audit.items() if node['title']=='desktop.step'}
    jev_calls=0
    for oid,step in steps.items():
        events=step.get('decision_events',[])
        requests=[e for e in events if e['kind']=='decision.requested']
        selected=next((e for e in reversed(events) if e['kind']=='decision.selected'),None)
        decision={'id':'decision:'+oid,'layer':2,'title': 'Jev · '+selected['action'] if selected else 'Jev 局部决策',
                  'engine':'Jev' if requests else 'Jev · 尚未调用','status':step['status'],'detail':step.get('detail',''),
                  'operation_id':oid,'events':step['events'],'decision_events':events,'error':step.get('error'),'children':[]}
        if selected:decision['detail']+=' · '+selected['ref']+' · 置信度 '+str(round(selected['confidence'],3))
        if requests:decision['detail']+=' · '+requests[0].get('model','Jev')
        if oid in owners:
            returned=[n['status'] for n in owners[oid]]
            decision['status']=next((v for v in ('completion_unknown','failed','denied','cancelled') if v in returned),decision['status'])
            decision['reused_operation']=len(owners[oid])>1
            decision['call_id']=owners[oid][0].get('call_id')
            decision['returned_status']=owners[oid][0].get('returned_status')
        owners[oid]=[decision];root['children'].append(decision);jev_calls+=len(requests)
    unmatched=[]
    for oid,node in audit.items():
        if oid in steps:continue
        cursor=oid;visited=set();owner=None
        while cursor and cursor not in visited:
            visited.add(cursor)
            if cursor in owners:owner=owners[cursor];break
            cursor=audit.get(cursor,{}).get('parent_operation')
        if owner is not None:
            for linked in owner:linked['children'].append({**node,'id':node['id']+':'+linked['id'],'reused_operation':len(owner)>1})
        else:unmatched.append(node)
    if unmatched:
        root['children'].append({'id':'unlinked:'+job['id'],'layer':2,'title':'未关联到 SDK 调用的 Runtime 记录','engine':'仅显示执行证据','status':'unlinked',
                                 'detail':'等待返回的 operation_id 建立关联，不推测所属决策。','children':unmatched})
    for cid,choice in choices.items():
        node=nodes[cid]
        if choice.get('tool')=='desktop.step':continue
        if not node['children'] and choice.get('operation_id'):
            node['children'].append({'id':'receipt:'+cid,'layer':3,'title':'MCP 返回回执','engine':'MCP','status':choice.get('returned_status',unreturned),
                                     'operation_id':choice['operation_id'],'detail':'尚无匹配的 Runtime 审计记录。','children':[],'events':[]})
    for cid,choice in choices.items():
        node=nodes[cid];node['returned_status']=choice.get('returned_status')
        primary=audit.get(choice.get('operation_id'))
        if primary:
            statuses=[choice.get('returned_status')]+[c['status'] for c in node['children']]
            node['status']=next((status for status in ('completion_unknown','failed','denied','cancelled','running','queued') if status in statuses),primary['status'])
    for oid in steps:
        node=owners[oid][0]
        if node['status']=='running' and job['status'] not in {'running','cancelling'}:
            in_flight=any(c['title'] in {'desktop.act','desktop.input'} and c['status'] in {'running','completion_unknown'} for c in node['children'])
            node['status']='completion_unknown' if in_flight else 'cancelled' if job['status']=='cancelled' else 'interrupted'
    root['architecture']['jev_active']=jev_calls>0
    root['detail']+=f' 本任务实际发起 {jev_calls} 次 Jev 请求。'
    root['counts']={'choices':len(choices),'operations':len(audit),'jev_calls':jev_calls}
    return root


def workflow_trace(run,state):
    root={'id':'run:'+run['id'],'layer':1,'title':run['workflow']['name'],'engine':'固定 Workflow','status':run['status'],
          'detail':'按保存的步骤执行；本次未调用 Planner 或 Jev。','architecture':{'planning':'Saved Workflow','selection':'Saved steps','execution':'Bokkio Runtime / Driver','jev_active':False},'children':[]}
    audit=operations(AuditStore(state),session_id=run['session_id'])
    grouped={}
    for oid,node in audit.items():
        cursor=oid;visited=set();context={}
        while cursor and cursor not in visited:
            visited.add(cursor);candidate=audit.get(cursor,{})
            if candidate.get('workflow_step'):context=candidate['workflow_step'];break
            cursor=candidate.get('parent_operation')
        if context.get('run_id')==run['id']:grouped.setdefault((context.get('cycle',1),context['step_id']),[]).append(node)
    cycles=range(1,run.get('cycle',1)+1)
    for cycle in cycles:
        for i,step in enumerate(run['workflow']['steps']):
            receipts=[r for r in run['steps'] if r['step_id']==step['id'] and r.get('cycle',1)==cycle]
            status=receipts[-1]['status'] if receipts else run['status'] if cycle==run.get('cycle',1) and i==run['index'] else 'pending'
            node={'id':f"step:{run['id']}:{cycle}:{step['id']}",'layer':2,'title':f"{i+1}. "+(step.get('label') or step['action']),
                  'engine':'固定步骤 · 无模型决策','status':status,'detail':f"第 {cycle} 轮 · "+step.get('window',''),
                  'verification':receipts[-1].get('verification') if receipts else None,'children':grouped.get((cycle,step['id']),[])}
            if run.get('verification_pending',{}).get('step_id')==step['id'] and cycle==run.get('cycle',1):node['verification']='failed' if run['status']=='failed' else 'pending'
            root['children'].append(node)
    return root
