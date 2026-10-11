import copy
import pytest
from bokkio import office_visual as visual
from bokkio.model import BokkioActionError,BokkioCompletionUnknown
from bokkio.windows_capture import CaptureError


def field():
    return {'platform':'macos','role':'combo_box','name':'Number Format','value':'General',
            'state':{'enabled':True},'bounds':{'x':-1,'y':10,'width':40,'height':20},
            'platform_data':{'mac_unique_identity':True,'ax_value_settable':True,'ax_original_actions':['AXConfirm']}}


@pytest.mark.parametrize('dispatched',[0,True,'unknown'])
def test_selection_button_refusal_never_reposts(monkeypatch,dispatched):
    from bokkio.model import BokkioStaleSnapshot
    setup(monkeypatch);posts=[]
    node={'ref':'button','role':'button','name':'Clear Formatting',
          'platform_data':{'mac_unique_identity':True,'ax_original_actions':['AXPress']}}
    editor={'ref':'editor','role':'text_area','children':[],
            'state':{'focused':True,'selected_text':'body'},'platform_data':{'mac_unique_identity':True}}
    reader=type('Reader',(),{'snapshot':lambda *args:{'windows':[editor]}})()
    def post(*a,**k):
        posts.append(k)
        raise CaptureError('native_button_changed','Selection changed',dispatched=dispatched)
    monkeypatch.setattr(visual,'perform',post)
    expected=BokkioStaleSnapshot if dispatched==0 else BokkioCompletionUnknown
    with pytest.raises(expected):visual.click_selection_button(10,'Owned',node,backend=reader)
    assert len(posts)==1 and posts[0]['_native_selection'] is editor


def test_selection_button_refuses_missing_focus_before_capture(monkeypatch):
    node={'role':'button','name':'Clear Formatting',
          'platform_data':{'mac_unique_identity':True,'ax_original_actions':['AXPress']}}
    reader=type('Reader',(),{'snapshot':lambda *args:{'windows':[]}})()
    monkeypatch.setattr(visual,'capture_window',lambda *a,**k:pytest.fail('No focused selection'))
    with pytest.raises(BokkioActionError,match='focused nonempty'):
        visual.click_selection_button(10,'Owned',node,backend=reader)


@pytest.mark.parametrize('permission',[False,True])
def test_button_foreground_change_can_refresh_only_before_posting_with_permission(monkeypatch,permission):
    from bokkio.model import BokkioStaleSnapshot
    setup(monkeypatch)
    node={'role':'button','name':'Clear Formatting',
          'platform_data':{'mac_unique_identity':True,'ax_original_actions':['AXPress']}}
    editor={'ref':'editor','role':'text_area','children':[],'state':{'selected_text':'body'},
            'platform_data':{'mac_unique_identity':True}}
    reader=type('Reader',(),{'snapshot':lambda *args:{'windows':[editor]}})()
    def refuse(*a,**k):
        raise CaptureError('input_unavailable','Foreground changed',dispatched=0,
                           input_scope={'event_permission':permission,'top_window_matches':False})
    monkeypatch.setattr(visual,'perform',refuse)
    expected=BokkioStaleSnapshot if permission else BokkioActionError
    with pytest.raises(expected):visual.click_selection_button(10,'Owned',node,backend=reader)


def setup(monkeypatch):
    from bokkio import macos_activation
    monkeypatch.setattr(macos_activation,'activate_window',lambda *a,**k:None)
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


def test_paragraph_numeric_field_checks_text_field_after_draft_commit(monkeypatch):
    setup(monkeypatch);node=field();node.update(role='text_field',name='At:',value='1.08',ref='spacing',children=[])
    node['platform_data']['mac_owner_pid']=10
    reader=type('Reader',(),{'snapshot':lambda *args:{'windows':[{**node,'value':'1.15'}]}})()
    calls=[]
    def post(*a,**k):
        calls.append(k);assert k['_post_verify']({},b'image')['passed']
        return {'status':'confirmed'}
    monkeypatch.setattr(visual,'perform',post)
    visual.replace_combo(10,'Paragraph',node,'1.15',backend=reader,confirm=False)
    assert len(calls)==1 and calls[0]['_end_field_edit'] is True


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


def test_delayed_native_value_is_observed_without_reposting(monkeypatch):
    setup(monkeypatch)
    node=field();node.update(ref='field',parent=None,children=[])
    node['platform_data']['mac_owner_pid']=10
    snapshots=[];posts=[];sleeps=[]
    class Reader:
        def snapshot(self,pid,title):
            assert (pid,title)==('10','Owned')
            fresh=copy.deepcopy(node)
            fresh['value']='General' if not snapshots else 'Currency'
            snapshots.append(fresh)
            return {'windows':[fresh]}
    def perform(*a,**k):
        posts.append(True)
        check=k['_post_verify']({},b'image')
        assert check['passed'] and check['observations']==2
        return {'status':'confirmed','verification':check}
    monkeypatch.setattr(visual,'perform',perform)
    monkeypatch.setattr(visual.time,'sleep',sleeps.append)
    result=visual.replace_combo(10,'Owned',node,'Currency',backend=Reader())
    assert result['confirmation_posted'] and len(posts)==1 and sleeps==[.1]


def test_native_readback_stops_when_binding_disappears(monkeypatch):
    setup(monkeypatch);node=field();node['ref']='field'
    class Reader:
        def snapshot(self,*a):return {'windows':[]}
    def perform(*a,**k):
        check=k['_post_verify']({},b'image')
        assert not check['passed'] and check['matching_targets']==0 and check['observations']==1
        return {'status':'unconfirmed'}
    monkeypatch.setattr(visual,'perform',perform)
    monkeypatch.setattr(visual.time,'sleep',lambda *a:pytest.fail('a lost binding must not be polled'))
    visual.replace_combo(10,'Owned',node,'Currency',backend=Reader())


def test_persistent_wrong_value_has_bounded_readbacks_and_one_dispatch(monkeypatch):
    setup(monkeypatch);node=field();node.update(ref='field',parent=None,children=[])
    node['platform_data']['mac_owner_pid']=10
    observations=[];posts=[]
    class Reader:
        def snapshot(self,*a):observations.append(True);return {'windows':[node]}
    def perform(*a,**k):
        posts.append(True);check=k['_post_verify']({},b'image')
        assert not check['passed'] and check['actual']=='General' and check['observations']==3
        raise CaptureError('input_completion_unknown','Posted input did not verify',dispatched=True,cause='native_readback_unconfirmed',verification=check)
    monkeypatch.setattr(visual,'perform',perform);monkeypatch.setattr(visual.time,'sleep',lambda *a,**k:None)
    with pytest.raises(BokkioCompletionUnknown,match='native_readback_unconfirmed'):
        visual.replace_combo(10,'Owned',node,'Currency',backend=Reader())
    assert len(observations)==3 and len(posts)==1


@pytest.mark.parametrize('popup',['Font','Save'])
def test_office_visual_observation_keeps_native_popup_without_capturing_source(monkeypatch,popup):
    from bokkio.visual_runtime import WindowScope
    snapshot={'windows':[{'role':'window','name':'Owned','children':[]},
                         {'role':'dialog','name':popup,'children':[]}]}
    native=type('Native',(),{'snapshot':lambda self,*a:snapshot})()
    backend=visual.OfficeVisualBackend(native,WindowScope('macos',10,'Owned',20))
    monkeypatch.setattr(backend.hybrid,'_capture',lambda *a,**k:pytest.fail('Popup must stay on native scope'))
    assert backend.observe_for_planner('10','Type title') is snapshot
    assert backend.execution_contract['visual_provider']=={'finish_typing':True}


def test_native_office_step_clears_old_visual_scope_before_save_dialog():
    from bokkio.visual_runtime import WindowScope
    reads=[]
    native=type('Native',(),{'snapshot':lambda self,app,window=None:reads.append((app,window)) or {'windows':[]}})()
    backend=visual.OfficeVisualBackend(native,WindowScope('macos',10,'Owned',20))
    backend.hybrid._active.add('10');backend.hybrid._contexts['10']={'obsolete':True}
    step={'window':'Save','allowed_values':['output.pptx'],
          'success':[{'role':'text_field','name':'Save As:','field':'value','equals':'output.pptx'}]}
    assert backend.prepare_step('10',{},step)=={'windows':[]}
    assert not backend.hybrid._active and not backend.hybrid._contexts and reads==[('10','Save')]


@pytest.mark.parametrize('changed_identity',[False,True])
def test_offscreen_option_is_realized_once_and_rebound_before_mouse_input(monkeypatch,changed_identity):
    def node(ref,role,parent,box,**data):
        return {'ref':ref,'role':role,'name':None,'value':None,'parent':parent,'children':[],
                'bounds':box,'state':{'visible':True},'platform':'macos','platform_data':data,'actions':[]}
    box=lambda y,h:{'x':30,'y':y,'width':100,'height':h}
    combo=node('combo','combo_box',None,box(20,20),ax_identifier='LatinID',mac_unique_identity=True)
    combo['name']='Latin text font:';combo['value']='Arial';combo['state']['expanded']=True
    clip=node('clip','group','combo',box(40,100),ax_role='AXScrollArea')
    items=node('list','list','clip',box(40,500),ax_role='AXList')
    option=node('choice','text_field','list',box(190,18),native_option_command=True,mac_unique_identity=True,ax_native_identity=123)
    option.update(name='Calibri',value='Calibri');option['state']['visible']=False
    bar=node('bar','scroll_bar','clip',box(40,100),numeric_value=0.)
    items['children']=[option];clip['children']=[items,bar];combo['children']=[clip]
    original=copy.deepcopy(option);scrolls=[];posts=[]
    class Reader:
        def snapshot(self,*args):return {'windows':[combo]}
        def perform(self,app,action,**kw):
            scrolls.append((app,action,kw));option['state']['visible']=True;option['bounds']=box(90,18)
            if changed_identity:option['platform_data']['ax_native_identity']=999
            return {'verification':'confirmed'}
    monkeypatch.setattr(visual,'capture_window',lambda *a,**k:({},b'image'))
    def perform(*args,**kwargs):
        posts.append(kwargs);assert kwargs['_native_option'] is True
        assert kwargs['_native_target']['platform_data']['native_option_viewport']==clip['bounds']
        combo['value']='Calibri';combo['state']['expanded']=False
        assert kwargs['_post_verify']({},b'image')['passed']
        return {'status':'confirmed'}
    monkeypatch.setattr(visual,'perform',perform)
    if changed_identity:
        with pytest.raises(BokkioActionError,match='identity changed'):
            visual.select_option(10,'Font',original,backend=Reader())
        assert not posts
    else:
        result=visual.select_option(10,'Font',original,backend=Reader())
        assert result['action_source']=='bounded_native_option_click' and len(posts)==1
    assert len(scrolls)==1 and scrolls[0][1]=='scroll' and 0<scrolls[0][2]['amount']<=1


def test_changed_native_field_before_posting_requests_observation_instead_of_replan(monkeypatch):
    from bokkio.model import BokkioStaleSnapshot
    setup(monkeypatch)
    monkeypatch.setattr(visual,'perform',lambda *a,**k:(_ for _ in ()).throw(
        CaptureError('native_field_changed','Observed field changed',dispatched=0)))
    with pytest.raises(BokkioStaleSnapshot):visual.replace_combo(10,'Owned',field(),'Currency')
