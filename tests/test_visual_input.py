import hashlib
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import pytest

from bokkio import visual_input as inputs
from bokkio.windows_capture import CaptureError


@pytest.fixture
def sample(monkeypatch):
    png=b'input source contract';digest=hashlib.sha256(png).hexdigest()
    meta={'schema':'bokkio.window_capture.v1','platform':'macos','pid':10,'window_id':20,'width':100,'height':100,
          'image_sha256':digest,'captured_at_unix_ns':time.time_ns(),'process_started_seconds_microseconds':'123:456',
          'content_rect':{'x':20,'y':30,'width':100,'height':100},'window_bounds':{'x':20,'y':30,'width':100,'height':100},
          'ocr':{'image_sha256':digest,'observations':[{'text':'Run check','confidence':1.,'bounds':{'x':10,'y':10,'width':30,'height':20}}]}}
    monkeypatch.setattr(inputs.sys,'platform','darwin');monkeypatch.setattr(inputs,'_helper',lambda:Path('/fake/helper'))
    return meta,png


def test_cancel_before_native_dispatch(sample,monkeypatch):
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('must not dispatch'))
    with pytest.raises(CaptureError) as caught:inputs.perform(*sample,'Run check','click',expect_text='Done',control=lambda:'cancel')
    assert caught.value.code=='input_cancelled' and caught.value.details['dispatched']==0


@pytest.mark.parametrize('action,value,expected',[('drag',None,'invalid_input'),('type','\n','invalid_input'),
                                                ('type','x'*1001,'invalid_input'),('click','x','invalid_input'),
                                                ('click',None,'verification_required')])
def test_invalid_action_literal_or_missing_verification_rejected(sample,monkeypatch,action,value,expected):
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('must not dispatch'))
    with pytest.raises(CaptureError) as caught:
        inputs.perform(*sample,'Run check',action,value=value,expect_text=None if expected=='verification_required' else 'Done')
    assert caught.value.code==expected


def test_native_scene_refusal_preserves_zero_dispatch(sample,monkeypatch):
    receipt={'error':'input_desktop_unavailable','message':'Input scene unavailable','details':{'dispatched':0}}
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:SimpleNamespace(stdout=json.dumps(receipt).encode(),returncode=1))
    with pytest.raises(CaptureError) as caught:inputs.perform(*sample,'Run check','click',expect_text='Done')
    assert caught.value.code=='input_desktop_unavailable' and caught.value.details['dispatched']==0


def test_missing_receipt_never_retries_input(sample,monkeypatch):
    calls=[]
    def timeout(*args,**kwargs):calls.append(args);raise subprocess.TimeoutExpired('helper',10)
    monkeypatch.setattr(subprocess,'run',timeout)
    with pytest.raises(CaptureError) as caught:inputs.perform(*sample,'Run check','click',expect_text='Done')
    assert len(calls)==1 and caught.value.code=='input_completion_unknown'


def test_posted_without_verified_output_remains_unknown(sample,monkeypatch):
    receipt={'pid':10,'window_id':20,'status':'posted_unverified','dispatched':True,'events_posted':2}
    calls=[]
    def run(*a,**k):calls.append(json.loads(k['input']));return SimpleNamespace(stdout=json.dumps(receipt).encode(),returncode=0)
    monkeypatch.setattr(subprocess,'run',run)
    monkeypatch.setattr(inputs,'capture_window',lambda *a,**k:sample)
    with pytest.raises(CaptureError) as caught:inputs.perform(*sample,'Run check','click',expect_text='Done')
    assert caught.value.code=='input_completion_unknown' and len(calls)==1
    assert calls[0]['expected_content_rect']==sample[0]['content_rect']


def test_literal_validation_with_explicit_verification(sample,monkeypatch):
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('must not dispatch'))
    for value in ['\n','x'*1001,'']:
        with pytest.raises(CaptureError) as caught:inputs.perform(*sample,'Run check','type',value=value,expect_text='Done')
        assert caught.value.code=='invalid_input'


def test_replace_posts_once_and_verifies_output_in_bound_field(sample,monkeypatch):
    import copy
    receipt={'pid':10,'window_id':20,'status':'posted_unverified','dispatched':True,'events_posted':8}
    requests=[]
    def run(*a,**k):requests.append(json.loads(k['input']));return SimpleNamespace(stdout=json.dumps(receipt).encode(),returncode=0)
    after=copy.deepcopy(sample[0])
    after['ocr']['observations']=[{'text':'Done','confidence':1.,'bounds':{'x':10,'y':10,'width':30,'height':20}},
                                  {'text':'Done','confidence':1.,'bounds':{'x':60,'y':60,'width':30,'height':20}}]
    monkeypatch.setattr(subprocess,'run',run);monkeypatch.setattr(inputs,'capture_window',lambda *a,**k:(after,sample[1]))
    region={'x':0,'y':0,'width':50,'height':50}
    result=inputs.perform(*sample,'Run check','replace',value='Done',expect_text='Done',verification_region=region)
    assert result['status']=='confirmed' and len(requests)==1
    assert requests[0]['action']=='replace' and requests[0]['text']=='Done'


@pytest.mark.parametrize('value',['','\n','a'*1001])
def test_replace_rejects_unbounded_or_control_text(sample,monkeypatch,value):
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('must not dispatch'))
    with pytest.raises(CaptureError,match='bounded literal'):
        inputs.perform(*sample,'Run check','replace',value=value,expect_text='Done')


def test_native_bounds_target_does_not_require_ambiguous_ocr_glyph(sample,monkeypatch):
    receipt={'pid':10,'window_id':20,'status':'posted_unverified','dispatched':True,'events_posted':8}
    requests=[]
    def run(*a,**k):requests.append(json.loads(k['input']));return SimpleNamespace(stdout=json.dumps(receipt).encode(),returncode=0)
    monkeypatch.setattr(subprocess,'run',run);monkeypatch.setattr(inputs,'capture_window',lambda *a,**k:sample)
    target={'ref':'owned-field','platform':'macos','role':'combo_box','state':{'enabled':True},
            'bounds':{'x':30,'y':40,'width':30,'height':20},
            'platform_data':{'mac_unique_identity':True,'mac_owner_pid':10,'ax_value_settable':True,'ax_original_actions':['AXConfirm']}}
    result=inputs.perform(*sample,'O66','replace',value='D:D',expect_text='D1',_native_target=target,
                          _post_verify=lambda *a:{'passed':True,'actual':'D1'})
    assert result['target']['source']=='native_bounds_bound_to_capture'
    assert requests[0]['point']=={'x':45,'y':50} and len(requests)==1
    target['platform_data']['mac_owner_pid']=99
    with pytest.raises(CaptureError,match='uniquely bound'):
        inputs.perform(*sample,'O66','replace',value='D:D',expect_text='D1',_native_target=target)
    assert len(requests)==1


def test_native_readback_failure_after_posting_remains_unknown(sample,monkeypatch):
    from bokkio.model import BokkioError
    receipt={'pid':10,'window_id':20,'status':'posted_unverified','dispatched':True,'events_posted':2}
    calls=[]
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:calls.append(True) or SimpleNamespace(stdout=json.dumps(receipt).encode(),returncode=0))
    monkeypatch.setattr(inputs,'capture_window',lambda *a,**k:sample)
    def verify(*a):raise BokkioError('The document window closed')
    with pytest.raises(CaptureError) as caught:
        inputs.perform(*sample,'Run check','click',expect_text='Done',_post_verify=verify)
    assert caught.value.code=='input_completion_unknown' and caught.value.details['dispatched'] is True
    assert len(calls)==1
