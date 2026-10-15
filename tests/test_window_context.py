import copy,os
import pytest
from test_runtime_workflow import setup
from bokkio.runtime_workflow import SCHEMA_V2

def test_window_title_changes_keep_same_native_instance(setup):
    desktop,client,runner,doc,library=setup
    doc=copy.deepcopy(doc);doc['schema']=SCHEMA_V2;doc['steps'][0]['window_context']={'key':'recorded','identity':'hwnd:42','role':'window','class_name':'Editor'}
    client.call('desktop.launch',{'app':'lab'})
    title=['Renamed Document'];desktop.windows=lambda app:[{'ref':'new-window-ref','role':'window','name':title[0],'platform_data':{'native_stable_id':'hwnd:0x2a','class_name':'Editor'}}]
    s=runner._context_step({'bindings':{'lab':os.getpid()},'id':'a'*32},doc['steps'][0]);assert s['window']=='Renamed Document' and s['target']['ancestors'][0]['name']=='Renamed Document'
    title[0]='Changed Again';run={'bindings':{'lab':os.getpid()},'id':'b'*32};first=runner._context_step(run,doc['steps'][0]);title[0]='Third Title';second=runner._context_step(run,doc['steps'][0]);assert second['window']=='Third Title'

def test_context_rejects_ambiguous_restart_window(setup):
    desktop,client,runner,doc,_=setup
    client.call('desktop.launch',{'app':'lab'})
    step=copy.deepcopy(doc['steps'][0]);step['window_context']={'key':'recorded','identity':'hwnd:42','role':'window'}
    desktop.windows=lambda app:[{'ref':str(i),'role':'window','name':'Other '+str(i),'platform_data':{'native_stable_id':'hwnd:'+str(i)}}for i in (1,2)]
    with pytest.raises(ValueError,match='ambiguous'):runner._context_step({'bindings':{'lab':os.getpid()},'id':'c'*32},step)
