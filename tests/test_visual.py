import copy
import hashlib
import time

import pytest

from bokkio.visual import find_text, validate_capture
from bokkio.macos_capture import screen_point
from bokkio.windows_capture import CaptureError


@pytest.fixture
def sample():
    image=b'synthetic image contract';digest=hashlib.sha256(image).hexdigest()
    metadata={'schema':'bokkio.window_capture.v1','platform':'macos','pid':101,'window_id':202,
              'width':1280,'height':720,'content_rect':{'x':-100,'y':50,'width':640,'height':360},
              'captured_at_unix_ns':time.time_ns(),'image_sha256':digest,
              'ocr':{'image_sha256':digest,'observations':[
                  {'text':'Run check','confidence':.99,'bounds':{'x':100,'y':200,'width':120,'height':32}},
                  {'text':'Ready','confidence':1.,'bounds':{'x':40,'y':500,'width':60,'height':20}}]}}
    return metadata,image


def test_ocr_candidate_uses_image_to_screen_points_without_authorizing_action(sample):
    meta,image=sample;found=find_text(meta,image,'Run check')
    assert found['center_image']=={'x':160.,'y':216.}
    assert found['center_screen']=={'x':-20.,'y':158.}
    assert found['pid']==101 and found['window_id']==202 and not found['action_authorized']


def test_duplicate_text_requires_distinguishing_region(sample):
    meta,image=sample;meta['ocr']['observations'].append({'text':'Run check','confidence':1.,'bounds':{'x':600,'y':400,'width':120,'height':32}})
    with pytest.raises(CaptureError) as caught:find_text(meta,image,'Run check')
    assert caught.value.code=='visual_ambiguous'
    found=find_text(meta,image,'Run check',region={'x':0,'y':0,'width':400,'height':400})
    assert found['bounds']['x']==100


@pytest.mark.parametrize('target,threshold',[('Missing',.8),('run check',.8),('Run check',1.)])
def test_no_guess_for_absence_case_or_low_confidence(sample,target,threshold):
    with pytest.raises(CaptureError) as caught:find_text(*sample,target,confidence=threshold)
    assert caught.value.code=='visual_missing'


@pytest.mark.parametrize('mutate,code',[
    ('image','image_mismatch'),('ocr','ocr_mismatch'),('old','capture_stale'),('future','capture_stale'),
    ('negative_bounds','invalid_ocr'),('nan_score','invalid_ocr'),('missing_dimension','invalid_capture')])
def test_changed_or_invalid_contract_rejected(sample,mutate,code):
    meta,image=sample
    if mutate=='image':image=b'changed'
    if mutate=='ocr':meta['ocr']['image_sha256']='changed'
    if mutate=='old':meta['captured_at_unix_ns']-=61_000_000_000
    if mutate=='future':meta['captured_at_unix_ns']+=61_000_000_000
    if mutate=='negative_bounds':meta['ocr']['observations'][0]['bounds']['x']=-1
    if mutate=='nan_score':meta['ocr']['observations'][0]['confidence']=float('nan')
    if mutate=='missing_dimension':meta.pop('width')
    with pytest.raises(CaptureError) as caught:find_text(meta,image,'Run check')
    assert caught.value.code==code


@pytest.mark.parametrize('region',[{'x':-1,'y':0,'width':10,'height':10},{'x':0,'y':0,'width':0,'height':10},
                                   {'x':1200,'y':0,'width':100,'height':10},{'x':True,'y':0,'width':10,'height':10}])
def test_invalid_region(sample,region):
    with pytest.raises(CaptureError) as caught:find_text(*sample,'Run check',region=region)
    assert caught.value.code=='invalid_region'


def test_coordinate_mapping_rejects_out_of_range(sample):
    meta,_=sample
    for x,y in [(1280,0),(0,720),(-1,0),(float('inf'),0),(True,0)]:
        with pytest.raises(CaptureError):screen_point(meta,x,y)


def test_invalid_metadata_and_excessive_ocr_are_structured(sample):
    meta,image=sample
    with pytest.raises(CaptureError) as caught:find_text([],image,'Run check')
    assert caught.value.code=='invalid_capture'
    meta['ocr']['observations']*=1025
    with pytest.raises(CaptureError) as caught:find_text(meta,image,'Run check')
    assert caught.value.code=='invalid_ocr'
