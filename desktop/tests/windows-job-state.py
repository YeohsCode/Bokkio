import pathlib,sys,sqlite3,json
state=pathlib.Path(sys.argv[1]);cid=sys.argv[2]
db=sqlite3.connect(state/'runtime.sqlite3');db.row_factory=sqlite3.Row
rows=[dict(r) for r in db.execute("SELECT j.id,j.status,j.cancel,j.request,s.policy FROM jobs j JOIN sessions s ON j.session_id=s.id") if json.loads(r['policy']).get('task_id')==cid]
print(json.dumps([{**{k:v for k,v in r.items() if k in ['status','cancel']},'code_has_delay':'time.sleep(12)' in json.loads(r['request']).get('code','')} for r in rows]))
