import json
from io import BytesIO
from pathlib import Path

import pytest

from bokkio.model import BokkioError
from bokkio.office_judge import judge
from bokkio.office_benchmark import load_bundle

BUNDLE=Path(__file__).resolve().parents[1]/'fixtures/windowsworld-office'


def test_original_judge_keeps_prompt_model_and_all_check_ids(tmp_path,monkeypatch):
    monkeypatch.setenv('QWEN_API_KEY','synthetic-test-key')
    image=tmp_path/'scope.png';image.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic')
    _,tasks=load_bundle(BUNDLE);task=tasks[0];checks=task['evaluation_metrics']['intermediate_checks']
    expected={'intermediate_results':{c:{'result':False,'reason':'no evidence'} for c in checks},'final_result':{'result':False,'reason':'no evidence'}}
    captured=[]
    def opener(request,timeout):
        captured.append(json.loads(request.data));return BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(expected)}}]}).encode())
    result=judge(BUNDLE,task['task_id'],[],[image],opener=opener)
    rubric=json.loads((BUNDLE/'judge-rubric.json').read_text())
    assert captured[0]['model']==rubric['model'] and captured[0]['messages'][0]['content']==rubric['system_prompt']
    assert not result['official_score'] and result['intermediate_score']==0


def test_missing_original_judge_credential_does_not_call_network(tmp_path,monkeypatch):
    monkeypatch.delenv('QWEN_API_KEY',raising=False);image=tmp_path/'x.png';image.write_bytes(b'x')
    with pytest.raises(BokkioError,match='QWEN_API_KEY'):
        judge(BUNDLE,'win_adm_l1_003',[],[image],opener=lambda *a,**k:pytest.fail('no network'))


def test_judge_cannot_silently_drop_a_checkpoint(tmp_path,monkeypatch):
    monkeypatch.setenv('QWEN_API_KEY','synthetic-test-key');image=tmp_path/'x.png';image.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic')
    answer={'intermediate_results':{},'final_result':{'result':True,'reason':'unsupported'}}
    def opener(*a,**k):return BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(answer)}}]}).encode())
    with pytest.raises(BokkioError,match='omitted'):
        judge(BUNDLE,'win_adm_l1_003',[],[image],opener=opener)
