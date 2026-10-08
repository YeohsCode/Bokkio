import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from bokkio import macos_capture as mac
from bokkio.windows_capture import CaptureError, _png


@pytest.fixture
def helper(monkeypatch):
    monkeypatch.setattr(mac.sys,'platform','darwin')
    monkeypatch.setattr(mac,'_helper',lambda:Path('/synthetic/helper'))
    def install(change=None,error=None):
        def run(command,*,input,**kwargs):
            if error:raise error
            args=json.loads(input);png=_png(2,1,bytes([3,2,1,0,6,5,4,0]))
            meta={'pid':args['pid'],'window_id':12,'width':2,'height':1,
                  'image_bytes':len(png),'image_sha256':hashlib.sha256(png).hexdigest()}
            if args['ocr']:meta['ocr']={'image_sha256':meta['image_sha256']}
            if change:change(meta)
            Path(args['output']).write_bytes(png)
            return SimpleNamespace(stdout=json.dumps({'metadata':meta}).encode(),returncode=0)
        monkeypatch.setattr(subprocess,'run',run)
    return install


def test_native_capture_checks_scope_png_and_ocr(helper):
    helper();meta,png=mac.capture_window(100,window_id=12,ocr=True)
    assert meta['pid']==100 and meta['ocr']['image_sha256']==hashlib.sha256(png).hexdigest()


@pytest.mark.parametrize('change',[
    lambda m:m.update(pid=101),lambda m:m.update(window_id=13),lambda m:m.update(width=3),
    lambda m:m.update(image_sha256='bad'),lambda m:m['ocr'].update(image_sha256='bad')])
def test_native_capture_rejects_wrong_identity_or_bytes(helper,change):
    helper(change)
    with pytest.raises(CaptureError) as caught:mac.capture_window(100,window_id=12,ocr=True)
    assert caught.value.code=='worker_failed'


def test_capture_timeout_kills_work_at_boundary(helper):
    helper(error=subprocess.TimeoutExpired('helper',.1))
    with pytest.raises(CaptureError) as caught:mac.capture_window(100,timeout=.1)
    assert caught.value.code=='capture_timeout'


@pytest.mark.parametrize('kwargs',[{'pid':True},{'pid':0},{'pid':1,'window_id':0},{'pid':1,'title':''},
                                   {'pid':1,'ocr':1},{'pid':1,'timeout':float('nan')}])
def test_invalid_scope_does_not_build_helper(monkeypatch,kwargs):
    monkeypatch.setattr(mac,'_helper',lambda:pytest.fail('must reject before helper build'))
    with pytest.raises(CaptureError):mac.capture_window(**kwargs)
