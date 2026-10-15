import copy
import pytest
from test_runtime_workflow import setup
from bokkio.runtime_workflow import SCHEMA_V2

def test_repair_zero_dispatch_preserves_completed_checkpoint(setup):
    desktop,client,runner,doc,library=setup;doc=copy.deepcopy(doc);doc['schema']=SCHEMA_V2;doc['steps'][0]['timeout']=.01;doc=library.save(doc,doc['sha256']);desktop.duplicate=True
    run=runner.run(runner.start(doc)['id']);assert run['status']=='failed' and desktop.clicks==0
    desktop.duplicate=False;runner.repair(run['id'],doc);result=runner.resume(run['id']);assert result['status']=='completed' and desktop.clicks==1

def test_repair_completion_check_never_redispatches(setup):
    desktop,client,runner,doc,library=setup;doc=copy.deepcopy(doc);doc['schema']=SCHEMA_V2;doc['steps'][0]['timeout']=.01;doc['steps'][0]['verify'][0]['equals']='wrong';doc=library.save(doc,doc['sha256']);run=runner.run(runner.start(doc)['id']);assert run['status']=='failed' and desktop.clicks==1
    doc['steps'][0]['verify'][0]['equals']='中文 hello';doc=library.save(doc,doc['sha256']);repaired=runner.repair(run['id'],doc);assert repaired['repairs'][-1]['mode']=='verify';assert runner.resume(run['id'])['status']=='completed' and desktop.clicks==1

def test_repair_cannot_change_already_dispatched_input(setup):
    desktop,client,runner,doc,library=setup;doc=copy.deepcopy(doc);doc['schema']=SCHEMA_V2;doc['steps'][0]['timeout']=.01;doc['steps'][0]['verify'][0]['equals']='wrong';doc=library.save(doc,doc['sha256']);run=runner.run(runner.start(doc)['id']);doc['steps'][0]['arguments']['value']='different';doc=library.save(doc,doc['sha256'])
    with pytest.raises(ValueError,match='already ran'):runner.repair(run['id'],doc)
    assert desktop.clicks==1

def test_repair_cannot_rebind_already_dispatched_application(setup):
    desktop,client,runner,doc,library=setup;doc=copy.deepcopy(doc);doc['schema']=SCHEMA_V2;doc['steps'][0]['timeout']=.01;doc['steps'][0]['verify'][0]['equals']='wrong';doc=library.save(doc,doc['sha256']);run=runner.run(runner.start(doc)['id']);alias=doc['steps'][0]['app'];doc['apps'][alias]['name']='Different App';doc=library.save(doc,doc['sha256'])
    with pytest.raises(ValueError,match='original application'):runner.repair(run['id'],doc)
    assert desktop.clicks==1
