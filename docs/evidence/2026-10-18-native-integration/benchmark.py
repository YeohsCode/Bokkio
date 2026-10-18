"""Synthetic provider work, not OS latency or business task success."""
import argparse,json,statistics,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--tests',required=True);p.add_argument('--platform',default='windows');p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,a.source);sys.path.insert(0,a.tests)
from bokkio.xa11y_backend import Xa11yBackend
from test_cli import App,Element,FakeXa11y
rows=[]
for _ in range(9):
    counters={'children_calls':0}
    def e(role,name,children=None):
        item=Element(role,name,children=children)
        original=item.children
        def children():counters['children_calls']+=1;return original()
        item.children=children;return item
    windows=[e('window','Document '+str(i),[e('button','Cell '+str(j)) for j in range(300)]) for i in range(10)]
    app=App(windows[0]);app.element.children_values=windows;original=app.element.children
    app.element.children=lambda:counters.update(children_calls=counters['children_calls']+1) or original()
    backend=Xa11yBackend(FakeXa11y(),platform=a.platform);backend._resolve_app=lambda _:app
    start=time.perf_counter();s=backend.snapshot('app','Document 5');elapsed=time.perf_counter()-start
    rows.append({**counters,'elapsed_ms':elapsed*1000,'target_ref':s['windows'][0]['children'][0]['ref']})
result={'kind':'synthetic_provider','platform_adapter':a.platform,'windows':10,'nodes_per_window':301,'iterations':len(rows),'children_calls':rows[0]['children_calls'],'elapsed_ms_median':statistics.median(x['elapsed_ms'] for x in rows),'target_ref':rows[0]['target_ref'],'samples':rows,'business_success_rate':None,'native_provider_calls_measured':False}
Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
