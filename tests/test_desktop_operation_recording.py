import copy
import pytest
from bokkio.desktop_service import DesktopStudio
from bokkio.workflow import save_json
from bokkio.runtime_workflow import validate_document
from test_runtime_workflow import setup


def test_interrupted_operation_draft_keeps_steps(tmp_path):
    state=tmp_path/'studio';state.mkdir()
    original={'id':'a'*32,'name':'Recorded operations','steps':[{'id':'step','action':'click','recorded_at':2}],'recording':{'started_at':1}}
    path=state/'workflow-drafts'/('a'*32+'.json')
    save_json(path,{'status':'paused','document':original,'issues':[]})
    studio=DesktopStudio(state)
    try:
        recovered=studio.route('GET','/api/draft',{'id':['a'*32]})
        assert recovered['status']=='interrupted'
        assert recovered['document']==original
    finally:studio.close()


@pytest.mark.parametrize('field',['video_id','video_offset'])
def test_video_step_fields_are_not_workflow_fields(setup,field):
    *_,doc,library=setup
    doc=copy.deepcopy(doc);doc['schema']='bokkio.runtime-workflow.v2'
    doc['steps'][0][field]='removed'
    with pytest.raises(ValueError,match='Invalid workflow step'):validate_document(doc)


def test_video_metadata_is_not_recording_metadata(setup):
    *_,doc,library=setup
    doc=copy.deepcopy(doc);doc['schema']='bokkio.runtime-workflow.v2'
    doc['recording']={'video_id':'b'*32}
    with pytest.raises(ValueError,match='Invalid recording metadata'):validate_document(doc)


def test_desktop_has_no_video_setting_or_route(tmp_path):
    studio=DesktopStudio(tmp_path)
    try:
        with pytest.raises(ValueError,match='Unknown settings'):
            studio.route('POST','/api/settings',{'capture_video':True})
        with pytest.raises(ValueError,match='Unknown desktop route'):
            studio.route('POST','/api/draft/video',{})
    finally:studio.close()
