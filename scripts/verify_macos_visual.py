"""Native Mac capture/OCR candidate acceptance on owned painted windows.

No input is dispatched. Pixel geometry, OCR bounds and rejection paths are
checked independently of AX, CUA or model providers.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time
import zlib

from bokkio.macos_capture import capture_window
from bokkio.windows_capture import CaptureError, save_capture
from bokkio.visual import find_text


def decode_png(data):
    if data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Not PNG')
    position=8;compressed=b''
    while position<len(data):
        size=struct.unpack('>I',data[position:position+4])[0]
        kind=data[position+4:position+8];body=data[position+8:position+8+size]
        if zlib.crc32(kind+body)!=struct.unpack('>I',data[position+8+size:position+12+size])[0]:raise ValueError('CRC mismatch')
        if kind==b'IHDR':
            width,height,bits,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',body)
            if bits!=8 or color not in {2,6} or compression or filtering or interlace:raise ValueError('Unsupported PNG format')
        if kind==b'IDAT':compressed+=body
        position+=size+12
    channels=4 if color==6 else 3;stride=width*channels;raw=zlib.decompress(compressed)
    if len(raw)!=height*(stride+1):raise ValueError('Invalid rows')
    rows=[];previous=bytearray(stride)
    def paeth(a,b,c):
        p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
        return a if pa<=pb and pa<=pc else b if pb<=pc else c
    for y in range(height):
        offset=y*(stride+1);kind=raw[offset];row=bytearray(raw[offset+1:offset+1+stride])
        if kind>4:raise ValueError('Unknown PNG filter')
        for x in range(stride):
            left=row[x-channels] if x>=channels else 0;up=previous[x];corner=previous[x-channels] if x>=channels else 0
            predictor=[0,left,up,(left+up)//2,paeth(left,up,corner)][kind]
            row[x]=(row[x]+predictor)&255
        rows.append(row);previous=row
    return width,height,lambda x,y:tuple(rows[y][x*channels:x*channels+3])


def run(fixture,output):
    output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[1]
    files=['src/bokkio/macos_capture.py','src/bokkio/native/macos_capture.swift','src/bokkio/visual.py',
           'src/bokkio/windows_capture.py','src/bokkio/cli.py','scripts/verify_macos_visual.py','fixtures/cocoa-visual/main.swift']
    summary={'scope':'p7_macos_capture_ocr_native','normal_runs':[],'rejections':[],
             'planned':{'normal_runs':3},'input_dispatched':False,
             'source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
             'fixture_sha256':hashlib.sha256((fixture/'Contents/MacOS'/fixture.stem).read_bytes()).hexdigest()}
    def persist():(output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    def start(label,**flags):
        env=dict(os.environ)
        for key in ['BOKKIO_VISUAL_DUPLICATE','BOKKIO_VISUAL_WINDOWS','BOKKIO_VISUAL_MINIMIZE']:env.pop(key,None)
        state=output/(label+'.state.json');env['BOKKIO_VISUAL_STATE']=str(state);env.update(flags)
        p=subprocess.Popen([str(fixture/'Contents/MacOS'/fixture.stem)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        until=time.monotonic()+10
        while time.monotonic()<until:
            if state.exists():
                try:return p,json.loads(state.read_text())
                except (OSError,ValueError):pass
            if p.poll() is not None:raise RuntimeError('Fixture exited before readiness')
            time.sleep(.1)
        p.terminate();p.wait(timeout=10);raise RuntimeError('Fixture readiness timed out')
    def stop(p):
        if p.poll() is None:p.terminate();p.wait(timeout=10)
    def reject(label,expected,call):
        try:call()
        except CaptureError as error:
            row={'case':label,'expected':expected,'actual':error.as_dict(),'passed':error.code==expected}
            summary['rejections'].append(row);persist()
            if not row['passed']:raise RuntimeError('Unexpected rejection')
            return
        raise RuntimeError('Unsafe/ambiguous case was accepted')
    persist()
    try:
        for i in range(1,4):
            p,state=start(f'normal-{i}')
            try:
                meta,png=capture_window(p.pid,title='BokkioVisual',ocr=True,timeout=15)
                save_capture(meta,png,output/f'normal-{i}.png')
                selected={text:find_text(meta,png,text,max_age=30) for text in ['Run check','Enter code','Ready']}
                w,h,pixel=decode_png(png);r=meta['content_rect'];scale_x=w/r['width'];scale_y=h/r['height']
                title_height=r['height']-state['client_height']
                def inside(text,box):
                    center=selected[text]['center_image'];x=center['x']/scale_x;y=center['y']/scale_y-title_height
                    return box[0]<=x<=box[0]+box[2] and box[1]<=y<=box[1]+box[3]
                marks=[pixel(round(12*scale_x),round((title_height+12)*scale_y)),
                       pixel(round((r['width']-20)*scale_x),round((title_height+12)*scale_y)),
                       pixel(round(12*scale_x),round((r['height']-20)*scale_y)),
                       pixel(round((r['width']-20)*scale_x),round((r['height']-20)*scale_y))]
                colors=[m[0]>100 and m[2]>100 and m[1]<80 for m in marks[:1]]+[
                    marks[1][1]>120 and marks[1][0]<80,marks[2][0]>120 and marks[2][1]<100,
                    marks[3][2]>120 and marks[3][0]<100]
                checks={'identity':meta['pid']==p.pid and meta['window_id']==state['window_id'],
                        'geometry':r==state['expected_content_rect'],'png_dimensions':(w,h)==(meta['width'],meta['height']),
                        'painted_marks':all(colors),'button_center':inside('Run check',(60,175,210,52)),
                        'input_label_center':inside('Enter code',(60,100,340,48)),
                        'screen_coordinate_mapping':abs(selected['Run check']['center_screen']['x']-(r['x']+selected['Run check']['center_image']['x']/scale_x))<.001,
                        'no_internal_controls':state['subviews']==0,'not_action_authorized':not selected['Run check']['action_authorized']}
                row={'run':i,'pid':p.pid,'window_id':meta['window_id'],'checks':checks,'passed':all(checks.values()),'candidates':selected}
                summary['normal_runs'].append(row);persist();print(json.dumps(row),flush=True)
                if not row['passed']:raise RuntimeError('Capture/OCR/geometry independent checks failed')
                if i==1:
                    reject('unknown_text','visual_missing',lambda:find_text(meta,png,'Absent',max_age=30))
                    reject('tampered_image','image_mismatch',lambda:find_text(meta,png+b'x','Run check',max_age=30))
                    old=copy.deepcopy(meta);old['captured_at_unix_ns']-=61_000_000_000
                    reject('stale_image','capture_stale',lambda:find_text(old,png,'Run check',max_age=30))
                    reject('wrong_window_id','window_missing',lambda:capture_window(p.pid,window_id=meta['window_id']+100000,timeout=15))
            finally:stop(p)
            if i==1:reject('closed_process','process_missing',lambda:capture_window(p.pid,title='BokkioVisual',timeout=15))
        p,state=start('duplicate',BOKKIO_VISUAL_DUPLICATE='1')
        try:
            meta,png=capture_window(p.pid,title='BokkioVisual',ocr=True,timeout=15);save_capture(meta,png,output/'duplicate.png')
            reject('duplicate_text','visual_ambiguous',lambda:find_text(meta,png,'Run check',max_age=30))
            title_height=meta['content_rect']['height']-state['client_height'];scale=meta['width']/meta['content_rect']['width']
            chosen=find_text(meta,png,'Run check',max_age=30,region={'x':40*scale,'y':(title_height+160)*scale,'width':250*scale,'height':80*scale})
            summary['duplicate_region']={'candidate':chosen,'passed':chosen['center_image']['x']/scale<300};persist()
        finally:stop(p)
        p,state=start('multiple',BOKKIO_VISUAL_WINDOWS='2')
        try:
            reject('duplicate_window_titles','window_ambiguous',lambda:capture_window(p.pid,title='BokkioVisual',timeout=15))
            meta,png=capture_window(p.pid,window_id=state['window_id'],ocr=True,timeout=15);save_capture(meta,png,output/'explicit-window.png')
            summary['explicit_window']={'passed':meta['window_id']==state['window_id']};persist()
        finally:stop(p)
        p,state=start('minimized',BOKKIO_VISUAL_MINIMIZE='1')
        try:
            time.sleep(.5)
            # ScreenCaptureKit may omit minimized windows from its list, or
            # return an offscreen record. Both reject input-target capture.
            try:capture_window(p.pid,window_id=state['window_id'],timeout=15)
            except CaptureError as error:
                row={'case':'minimized','actual':error.as_dict(),'passed':error.code in {'window_missing','window_not_visible'}}
                summary['rejections'].append(row);persist()
                if not row['passed']:raise RuntimeError('Unexpected minimized-window error')
            else:raise RuntimeError('Minimized fixture was captured as a target')
        finally:stop(p)
        summary['passed']=all(r['passed'] for r in summary['normal_runs']) and len(summary['normal_runs'])==3 and all(r['passed'] for r in summary['rejections']) and summary['duplicate_region']['passed'] and summary['explicit_window']['passed']
        persist();return summary['passed']
    except Exception as error:
        summary['passed']=False;summary['error']=error.as_dict() if isinstance(error,CaptureError) else str(error);persist();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(0 if run(args.fixture,args.output) else 1)
