import copy
import pytest
from bokkio import office_visual as visual
from bokkio.model import BokkioActionError,BokkioCompletionUnknown
from bokkio.windows_capture import CaptureError


def field():
    return {'platform':'macos','role':'combo_box','name':'Number Format','value':'General',
            'state':{'enabled':True},'bounds':{'x':-1,'y':10,'width':40,'height':20},
            'platform_data':{'mac_unique_identity':True,'ax_value_settable':True,'ax_original_actions':['AXConfirm']}}


def setup(monkeypatch):
    from bokkio import macos_activation
    monkeypatch.setattr(macos_activation,'activate_window',lambda *a:None)
    meta={'width':200,'height':200,'content_rect':{'x':0,'y':0,'width':100,'height':100}}
    monkeypatch.setattr(visual,'capture_window',lambda *a,**k:(meta,b'image'))


def test_office_value_transport_clips_to_owned_window_and_checks_same_field(monkeypatch):
    setup(monkeypatch);calls=[]
    def perform(*a,**k):calls.append(k);return {'status':'confirmed'}
    monkeypatch.setattr(visual,'perform',perform)
    result=visual.replace_combo(10,'Owned',field(),'Currency')
    assert result['confirmation_posted'] and result['action_source']=='bounded_visual_replace'
    assert calls[0]['region']=={'x':0,'y':20,'width':78,'height':40}
    assert calls[0]['verification_region']==calls[0]['region']
    assert calls[0]['expect_text']=='Currency'


def test_name_box_confirmation_checks_normalized_cell_label(monkeypatch):
    setup(monkeypatch);node=field();node.update(name='name box',value='A1');node['platform_data']['ax_identifier']='NameBox'
    calls=[]
    monkeypatch.setattr(visual,'perform',lambda *a,**k:calls.append(k) or {'status':'confirmed'})
    visual.replace_combo(10,'Owned',node,'D:D')
    assert calls[0]['expect_text']=='D1'
    with pytest.raises(BokkioActionError,match='A1 cell/range'):visual.replace_combo(10,'Owned',node,'https://example.test')
    assert len(calls)==1


def test_disabled_or_unbound_field_never_captures_or_posts(monkeypatch):
    monkeypatch.setattr(visual,'capture_window',lambda *a,**k:pytest.fail('must reject before capture'))
    node=field();node['state']['enabled']=False
    with pytest.raises(BokkioActionError):visual.replace_combo(10,'Owned',node,'Currency')
    node=field();node['platform_data']['mac_unique_identity']=False
    with pytest.raises(BokkioActionError):visual.replace_combo(10,'Owned',node,'Currency')


@pytest.mark.parametrize('dispatched',[True,'unknown',0])
def test_visual_failure_is_classified_without_retries(monkeypatch,dispatched):
    setup(monkeypatch);calls=[]
    def perform(*a,**k):calls.append(True);raise CaptureError('input_completion_unknown','unknown',dispatched=dispatched)
    monkeypatch.setattr(visual,'perform',perform)
    expected=BokkioCompletionUnknown if dispatched else BokkioActionError
    with pytest.raises(expected):visual.replace_combo(10,'Owned',field(),'Currency')
    assert len(calls)==1
