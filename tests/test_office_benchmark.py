import copy
import json
from pathlib import Path
import zipfile

import pytest

from bokkio.model import BokkioError
from bokkio.office_benchmark import BODY,TITLE,EXPENSES,load_bundle,evaluate,digest
from bokkio.office_runner import run

BUNDLE=Path(__file__).resolve().parents[1]/'fixtures/windowsworld-office'


def pack(path,files):
    with zipfile.ZipFile(path,'w') as z:
        for name,data in files.items():z.writestr(name,data)
    return path


def word(path,font='Calibri',line='276',heading='Heading1'):
    ns='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    paragraphs=''.join(f'<w:p><w:pPr><w:pStyle w:val="{heading if i==0 else "Normal"}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>' for i,text in enumerate([TITLE,*BODY]))
    return pack(path,{'word/document.xml':f'<w:document xmlns:w="{ns}"><w:body>{paragraphs}</w:body></w:document>',
        'word/styles.xml':f'<w:styles xmlns:w="{ns}"><w:style w:styleId="Heading1"><w:name w:val="heading 1"/></w:style><w:style w:styleId="Normal"><w:pPr><w:spacing w:line="{line}" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="{font}"/><w:sz w:val="22"/></w:rPr></w:style></w:styles>'})


def excel(path,code='$#,##0.00',header_style=True):
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    cells=[]
    for row,values in enumerate([['Date','Category','Description','Amount'],*EXPENSES],1):
        for col,value in zip('ABCD',values):
            style=' s="1"' if col=='D' and (row>1 or header_style) else ''
            content=f'<v>{value}</v>' if col=='D' and row>1 else f'<is><t>{value}</t></is>'
            type='' if col=='D' and row>1 else ' t="inlineStr"'
            cells.append(f'<c r="{col}{row}"{type}{style}>{content}</c>')
    return pack(path,{'xl/worksheets/sheet1.xml':f'<worksheet xmlns="{ns}"><sheetData><row>{"".join(cells)}</row></sheetData></worksheet>',
        'xl/styles.xml':f'<styleSheet xmlns="{ns}"><numFmts><numFmt numFmtId="164" formatCode="{code}"/></numFmts><cellXfs><xf numFmtId="0"/><xf numFmtId="164"/></cellXfs></styleSheet>'})


def deck(path,title='Alpha Initiative',layout='title'):
    return pack(path,{'ppt/slides/slide1.xml':f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:nvPr><p:ph type="ctrTitle"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{title}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>',
        'ppt/slides/_rels/slide1.xml.rels':'<Relationships><Relationship Type="x/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>',
        'ppt/slideLayouts/slideLayout1.xml':f'<sldLayout type="{layout}"/>'})


def test_pinned_selection_and_judge_preserved():
    manifest,tasks=load_bundle(BUNDLE)
    assert len(tasks)==3 and all(t['involved_apps'][0] in ['Word','Excel','PowerPoint'] for t in tasks)
    assert all(t['environment_setup']['urls_to_mock']==[] for t in tasks)
    assert manifest['source_task_count']==181


@pytest.mark.parametrize('font,line,heading',[('Arial','276','Heading1'),('Calibri','240','Heading1'),('Calibri','276','Normal')])
def test_word_independent_format_failures(tmp_path,font,line,heading):
    report=evaluate('win_adm_l1_003',word(tmp_path/'draft.docx',font,line,heading))
    assert report['checks']['preserved_content'] and not report['passed']


def test_word_resolves_inherited_formatting(tmp_path):
    assert evaluate('win_adm_l1_003',word(tmp_path/'draft.docx'))['passed']


@pytest.mark.parametrize('code,header',[('General',True),('[$-409]yyyy-mm-dd',True),('$#,##0.00',False)])
def test_excel_rejects_wrong_format_and_unformatted_header(tmp_path,code,header):
    report=evaluate('win_acc_l1_001',excel(tmp_path/'expenses.xlsx',code,header))
    assert report['checks']['preserved_values'] and not report['passed']


def test_excel_currency_preserves_values(tmp_path):
    assert evaluate('win_acc_l1_001',excel(tmp_path/'expenses.xlsx'))['passed']


@pytest.mark.parametrize('title,layout',[('Wrong','title'),('Alpha Initiative','blank')])
def test_ppt_title_and_layout_are_independent(tmp_path,title,layout):
    assert not evaluate('win_pro_l1_003',deck(tmp_path/'deck.pptx',title,layout))['passed']


def test_ppt_correct_and_missing_artifacts(tmp_path):
    assert evaluate('win_pro_l1_003',deck(tmp_path/'deck.pptx'))['passed']
    assert not evaluate('win_pro_l1_003',tmp_path/'missing.pptx')['passed']


def preparation(root):
    _,tasks=load_bundle(BUNDLE);records=[]
    for t in tasks:
        from bokkio.office_benchmark import TASKS
        id=t['task_id'];spec=TASKS[id];folder=root/id;desktop=folder/'desktop';desktop.mkdir(parents=True)
        file=desktop/spec['file'];source=file if spec['kind']!='powerpoint' else folder/'Bokkio_blank.pptx';source.write_bytes(b'owned initial input')
        records.append({'task_id':id,'app':spec['app'],'desktop':str(desktop),'artifact':str(file),'source':str(source),
                        'initial_inputs':{source.name:{'sha256':digest(source)}},'max_steps':15,'goal':t['instruction']})
    state={'schema':'bokkio.office_pilot.v1','revision':'fbccd464f94fec9e284e139f97bf96d0b192f580','scope':'unit_simulation',
           'bundle':str(BUNDLE),'bundle_manifest_sha256':digest(BUNDLE/'manifest.json'),'tasks':records}
    (root/'prepared.json').write_text(json.dumps(state));return state


def test_blocked_environment_never_constructs_agent_or_scores_tasks(tmp_path):
    preparation(tmp_path)
    def execute(*a):pytest.fail('agent must not start')
    report=run(tmp_path,environment=lambda:{'ready':False,'reason':'interactive_session_unavailable'},executor=execute)
    assert report['started']==0 and report['blocked']==3 and all(t['score'] is None for t in report['tasks'])
    with pytest.raises(BokkioError):run(tmp_path,environment=lambda:{'ready':False,'reason':'blocked'},executor=execute)


def test_setup_input_tampering_rejected_before_agent(tmp_path):
    state=preparation(tmp_path);Path(state['tasks'][0]['source']).write_bytes(b'changed')
    with pytest.raises(BokkioError,match='input changed'):run(tmp_path,environment=lambda:pytest.fail('must reject first'))


def test_model_completed_is_not_artifact_success(tmp_path):
    preparation(tmp_path)
    report=run(tmp_path,environment=lambda:{'ready':True},executor=lambda t,p:{'status':'completed','actions':1})
    assert report['started']==3 and report['status']=='completed' and report['passed']==0


def test_native_executor_constructs_real_agent_and_checks_saved_result(tmp_path,monkeypatch):
    import os
    import sys
    import time
    from types import SimpleNamespace
    from bokkio.agent import DesktopAgent
    from bokkio import office_runner,planner,jev,macos_activation
    from bokkio.xa11y_backend import Xa11yBackend
    state=preparation(tmp_path);task=next(t for t in state['tasks'] if t['task_id']=='win_adm_l1_003')
    artifact=Path(task['artifact']);word(artifact,font='Arial')
    monkeypatch.setitem(sys.modules,'xa11y',SimpleNamespace(App=SimpleNamespace(by_name=lambda *a,**k:SimpleNamespace(pid=123,windows=lambda:[SimpleNamespace(name=artifact.stem,activate=lambda:None)]))))
    monkeypatch.setattr(office_runner.subprocess,'run',lambda *a,**k:None)
    monkeypatch.setattr(office_runner.time,'sleep',lambda *a:None)
    monkeypatch.setattr(macos_activation,'activate_window',lambda *a:None)
    monkeypatch.setattr(Xa11yBackend,'snapshot',lambda *a,**k:{'windows':[]})
    monkeypatch.setattr(planner,'OpenRouterPlanner',lambda:object())
    monkeypatch.setattr(jev,'JevProvider',lambda:object())
    def execute(agent,goal,apps,path):
        assert isinstance(agent,DesktopAgent) and apps==['123'] and agent.max_actions==15
        assert agent.final_verifier({})[0] is False
        word(artifact)
        old=time.time_ns()-10_000_000_000
        os.utime(artifact,ns=(old,old))
        passed,detail=agent.final_verifier({})
        assert not passed and detail['score']['passed'] and not detail['score']['saved_after_start']
        fresh=time.time_ns()+1_000_000
        os.utime(artifact,ns=(fresh,fresh))
        assert agent.final_verifier({})[0] is True
        return {'status':'completed','actions':1}
    monkeypatch.setattr(DesktopAgent,'run',execute)
    assert office_runner._native_run(task,tmp_path/'agent.json')['status']=='completed'
