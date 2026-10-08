import base64
import hashlib
import json
import struct
import subprocess
from types import SimpleNamespace
import zlib

import pytest

from bokkio import windows_capture as capture
from bokkio.cli import main


def payload(pid=123, hwnd=456):
    png = capture._png(2, 1, bytes([3, 2, 1, 0, 6, 5, 4, 0]))
    metadata = {"pid":pid,"hwnd":hwnd,"image_sha256":hashlib.sha256(png).hexdigest(),"image_bytes":len(png)}
    return {"metadata":metadata,"png_base64":base64.b64encode(png).decode()}


@pytest.fixture
def fake_worker(monkeypatch):
    monkeypatch.setattr(capture.sys,"platform","win32")
    monkeypatch.setattr(subprocess,"CREATE_NO_WINDOW",0,raising=False)
    def install(data=None, error=None):
        def run(*args, **kwargs):
            if error: raise error
            return SimpleNamespace(stdout=json.dumps(data or payload()).encode(),returncode=0)
        monkeypatch.setattr(subprocess,"run",run)
    return install


def test_png_preserves_rgb_top_down_and_valid_crc():
    raw = bytes([3,2,1,0,6,5,4,0,9,8,7,0,12,11,10,0])
    png = capture._png(2,2,raw); position = 8; compressed = b""
    while position < len(png):
        length = struct.unpack(">I",png[position:position+4])[0]
        kind = png[position+4:position+8]; body = png[position+8:position+8+length]
        assert struct.unpack(">I",png[position+8+length:position+12+length])[0] == zlib.crc32(kind+body)
        if kind == b"IDAT": compressed += body
        position += length+12
    assert zlib.decompress(compressed) == bytes([0,1,2,3,4,5,6,0,7,8,9,10,11,12])


@pytest.mark.parametrize("pid,hwnd",[(True,None),(0,None),(-1,None),(1,False),(1,0),(1,-4)])
def test_invalid_scope_never_starts_worker(pid,hwnd,monkeypatch):
    monkeypatch.setattr(subprocess,"run",lambda *a,**k:pytest.fail("worker should not start"))
    with pytest.raises(capture.CaptureError,match="PID|HWND"): capture.capture_window(pid,hwnd)


@pytest.mark.parametrize("timeout",[float("nan"),float("inf"),0,16,True])
def test_invalid_timeout(timeout):
    with pytest.raises(capture.CaptureError) as caught: capture.capture_window(123,timeout=timeout)
    assert caught.value.code == "invalid_budget"


def test_worker_timeout_is_structured(fake_worker):
    fake_worker(error=subprocess.TimeoutExpired("worker",0.1))
    with pytest.raises(capture.CaptureError) as caught: capture.capture_window(123,456,timeout=0.1)
    assert caught.value.as_dict()["error"] == "capture_timeout"


@pytest.mark.parametrize("change",["pid","hwnd","sha","bytes"])
def test_worker_identity_and_image_tampering_rejected(fake_worker,change):
    data=payload(); key={"sha":"image_sha256","bytes":"image_bytes"}.get(change,change)
    data["metadata"][key] = "bad" if change=="sha" else 999
    fake_worker(data)
    with pytest.raises(capture.CaptureError) as caught: capture.capture_window(123,456)
    assert caught.value.code == "worker_failed"


def test_provider_permission_error_preserved(fake_worker):
    fake_worker({"error":"permission_denied","message":"Native capture denied","details":{"native_error":5}})
    with pytest.raises(capture.CaptureError) as caught: capture.capture_window(123,456)
    assert caught.value.as_dict()["details"] == {"native_error":5}


def test_coordinate_mapping_does_not_double_apply_dpi():
    metadata={"width":640,"height":360,"client_screen_origin":{"x":-1920,"y":120},"window_dpi":192}
    assert capture.screen_point(metadata,12.9,19.1)=={"x":-1908,"y":139}
    for x,y in [(640,0),(0,360),(-1,0),(float("nan"),0),(True,0)]:
        with pytest.raises(capture.CaptureError):capture.screen_point(metadata,x,y)


def test_save_refuses_overwrite_and_hash_mismatch(tmp_path):
    data=payload();png=base64.b64decode(data["png_base64"]);target=tmp_path/"scope.png"
    result=capture.save_capture(data["metadata"],png,target)
    assert target.read_bytes()==png
    assert json.loads((tmp_path/"scope.png.json").read_text())==data["metadata"]
    with pytest.raises(capture.CaptureError) as caught:capture.save_capture(data["metadata"],png,target)
    assert caught.value.code=="output_exists"
    with pytest.raises(capture.CaptureError):capture.save_capture(data["metadata"],b"bad",tmp_path/"other.png")
    assert not (tmp_path/"other.png").exists()


def test_cli_capture_works_without_ax_backend(fake_worker,monkeypatch,tmp_path,capsys):
    import bokkio.cli as cli
    monkeypatch.setattr(cli,"Xa11yBackend",lambda:pytest.fail("capture must not depend on AX"))
    fake_worker()
    assert main(["capture","--pid","123","--hwnd","0x1c8","--output",str(tmp_path/"scope.png")])==0
    assert json.loads(capsys.readouterr().out)["pid"]==123
