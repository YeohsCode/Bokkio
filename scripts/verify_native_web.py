"""Read-only live checks of the owned fixtures/native-web page in Chrome/Edge."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def verify(app, output):
    from bokkio.selector import flatten
    from bokkio.web_view import select_web
    from bokkio.xa11y_backend import Xa11yBackend
    snapshot=Xa11yBackend().snapshot(app)
    nodes,meta=select_web(snapshot)
    assert snapshot['read']['complete'] and meta['complete']
    original={n['ref']:n for n in flatten(snapshot['windows'])}
    selected={n['ref']:n for n in nodes}
    roots=[original[ref] for ref in meta['page_roots']]
    assert len(roots)==1 and roots[0]['name']=='Bokkio Native Web Fixture'
    page=list(flatten(roots))
    assert all(selected[n['ref']]==n for n in page)
    names={n['name'] for n in page}
    assert {'Required fact: shipping code BK-2718.','Blue pen','37','Red pen','19',
            'Tuesday at 10:30.','Nested required fact: aisle 4.','Send order'}<=names
    field=next(n for n in page if n['role']=='text_field' and n['name']=='Order reference')
    checkbox=next(n for n in page if n['role']=='check_box' and n['name']=='Approved')
    assert field['value']=='REF-2026' and checkbox['state']['checked'] is True
    cells=[n for n in page if n['role']=='table_cell']
    assert len(cells)==6
    assert all(original[n['parent']]['role']=='table_row' and
               original[original[n['parent']]['parent']]['role']=='table' for n in cells)
    result={'passed':True,'browser':snapshot['app']['name'],'read':snapshot['read'],
            'native_nodes':len(original),'selected_nodes':len(selected),'page_nodes':len(page),
            'all_page_refs_and_data_unchanged':True,'table_cells':len(cells),
            'required_facts_and_form_values':True,'nested_page_present':True,'view':meta}
    output.mkdir(parents=True,exist_ok=True)
    (output/'web-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',required=True,help='PID of the owned browser process')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(verify(args.app,args.output)))
