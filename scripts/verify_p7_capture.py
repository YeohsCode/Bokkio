"""P7.1 native capture acceptance on a disposable custom-drawn Windows fixture.

Fixture lifecycle and controlled faults are test setup. Production capture uses
Bokkio's scoped Win32 worker. No clicks, typing, OCR or model decisions here.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
import zlib

from bokkio.selector import flatten
from bokkio.windows_capture import CaptureError, capture_window, save_capture, screen_point
from bokkio.xa11y_backend import Xa11yBackend


def png_pixels(data):
    """Independent PNG parsing: check CRC, dimensions and RGB filter-0 rows."""
    if data[:8] != b"\x89PNG\r\n\x1a\n": raise ValueError("Not PNG")
    pos = 8; compressed = b""; width = height = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos+4])[0]
        kind = data[pos+4:pos+8]; body = data[pos+8:pos+8+length]
        if struct.unpack(">I",data[pos+8+length:pos+12+length])[0] != zlib.crc32(kind+body):
            raise ValueError("PNG CRC mismatch")
        if kind == b"IHDR":
            width,height,bits,color,compression,filters,interlace = struct.unpack(">IIBBBBB",body)
            if (bits,color,compression,filters,interlace)!=(8,2,0,0,0):raise ValueError("Unexpected PNG format")
        if kind == b"IDAT": compressed += body
        pos += length+12
    decoded = zlib.decompress(compressed);stride=width*3+1
    if len(decoded)!=height*stride or any(decoded[y*stride]!=0 for y in range(height)):
        raise ValueError("Invalid PNG rows")
    return width,height,lambda x,y:tuple(decoded[y*stride+1+x*3:y*stride+4+x*3])


def run(fixture, output, iterations=3):
    output.mkdir(parents=True,exist_ok=False)
    summary={"scope":"p7_1_native_windows_capture","normal_runs":[],"faults":[],
             "planned":{"normal_runs":iterations,"faults":["scope_mismatch","window_missing","minimized","ambiguous","protected","worker_timeout"]},
             "source_sha256":{str(p.relative_to(Path(__file__).resolve().parents[1])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__).resolve(),Path(__file__).resolve().parents[1]/'src/bokkio/windows_capture.py']},
             "fixture_sha256":hashlib.sha256(fixture.read_bytes()).hexdigest(),
             "input_dispatched":False,"passed":False}
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.MoveWindow.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.BOOL]
    user.MoveWindow.restype=wintypes.BOOL
    def persist(): (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def start(mode,label):
        path=output/(label+'.state.json');p=subprocess.Popen([str(fixture),str(path),mode])
        until=time.monotonic()+15
        while time.monotonic()<until:
            if path.is_file():
                try:return p,json.loads(path.read_text())
                except (ValueError,OSError):pass
            if p.poll() is not None:raise RuntimeError('Owned fixture exited before readiness')
            time.sleep(0.1)
        p.terminate();p.wait(timeout=5);raise RuntimeError('Owned fixture did not become ready')
    def stop(p):
        if p.poll() is None:p.terminate();p.wait(timeout=5)
    def failure(pid,hwnd,expected,**kwargs):
        try:capture_window(pid,hwnd,**kwargs)
        except CaptureError as error:
            row={'expected':expected,'actual':error.as_dict(),'passed':error.code==expected}
            summary['faults'].append(row);persist()
            if not row['passed']:raise RuntimeError('Unexpected native fault classification')
            return
        raise RuntimeError('Native capture accepted a fault scope')
    persist()
    try:
        for iteration in range(1,iterations+1):
            p,state=start('normal',f'normal-{iteration}')
            try:
                metadata,png=capture_window(p.pid,state['hwnd'])
                save_capture(metadata,png,output/f'normal-{iteration}.png')
                width,height,pixel=png_pixels(png)
                # Four independent painted corner marks detect offset, crop,
                # color-channel, blank-image and top-down row-order mistakes.
                markers=[pixel(12,12)==(161,11,206),pixel(width-20,12)==(19,203,101),
                         pixel(12,height-20)==(211,50,33),pixel(width-20,height-20)==(36,104,172)]
                mapped=screen_point(metadata,12,12)
                native= Xa11yBackend().snapshot(str(p.pid))
                (output/f'normal-{iteration}.native.json').write_text(json.dumps(native,indent=2)+'\n')
                checks={'markers':all(markers),'dimensions':(width,height)==(state['width'],state['height']),
                        'dpi':metadata['window_dpi']==state['dpi'],
                        'origin':metadata['client_screen_origin']=={'x':state['origin']['X'],'y':state['origin']['Y']},
                        'coordinate_mapping':mapped=={'x':state['origin']['X']+12,'y':state['origin']['Y']+12},
                        'zero_internal_controls':state['internal_control_count']==0,
                        'business_controls_hidden_from_AX':not any(n.get('name') in {'Run check','Enter code'} for n in flatten(native['windows'])),
                        'image_hash':hashlib.sha256(png).hexdigest()==metadata['image_sha256']}
                bounds=metadata['window_bounds']
                if not user.MoveWindow(state['hwnd'],bounds['x']+41,bounds['y']+29,bounds['width'],bounds['height'],True):
                    raise RuntimeError('Could not move owned fixture')
                moved,image=capture_window(p.pid,state['hwnd']);save_capture(moved,image,output/f'moved-{iteration}.png')
                checks['movement_changes_origin']=moved['client_screen_origin']=={'x':metadata['client_screen_origin']['x']+41,'y':metadata['client_screen_origin']['y']+29}
                checks['movement_preserves_pixels']=image==png
                row={'iteration':iteration,'pid':p.pid,'hwnd':state['hwnd'],'dpi':state['dpi'],'checks':checks,'passed':all(checks.values())}
                summary['normal_runs'].append(row);persist();print(json.dumps(row),flush=True)
                if not row['passed']:raise RuntimeError('Native capture pixel/geometry acceptance failed')
                if iteration==1:failure(p.pid+1,state['hwnd'],'scope_mismatch')
            finally:stop(p)
            if iteration==1:failure(p.pid,state['hwnd'],'window_missing')
        for mode,expected,budget in [('minimized','window_minimized',5),('multiple','window_ambiguous',5),('protected','capture_protected',5),('hang','capture_timeout',0.5)]:
            p,state=start(mode,mode)
            try:
                # Wait for post-Shown minimized/protection state to settle.
                time.sleep(0.25)
                failure(p.pid,None if mode=='multiple' else state['hwnd'],expected,timeout=budget)
            finally:stop(p)
        summary['passed']=len(summary['normal_runs'])==iterations and len(summary['faults'])==6
        persist();return summary['passed']
    except Exception as error:
        summary['error']=error.as_dict() if isinstance(error,CaptureError) else str(error);persist();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--iterations',type=int,choices=[1,3],default=3)
    args=parser.parse_args();raise SystemExit(0 if run(args.fixture,args.output,args.iterations) else 1)
