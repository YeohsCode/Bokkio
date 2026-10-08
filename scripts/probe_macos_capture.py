"""Probe scoped ScreenCaptureKit screenshots of fresh owned Cocoa fixtures.

This diagnostic is independent of CUA and xa11y. It does not dispatch input or
claim product-level visual fallback acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import time


def run(fixture, output, runs=3):
    if sys.platform != 'darwin':raise RuntimeError('Run the Mac probe on macOS')
    source=Path(__file__).parent/'native/macos_capture_probe.swift'
    executable=fixture/'Contents/MacOS'/fixture.stem
    if not executable.is_file():raise RuntimeError('Owned fixture executable is missing')
    output.mkdir(parents=True,exist_ok=False)
    helper=output/'capture-probe'
    subprocess.run(['swiftc','-framework','Cocoa','-framework','ScreenCaptureKit',str(source),'-o',str(helper)],check=True)
    summary={'scope':'owned_macos_screencapturekit_diagnostic','planned_runs':runs,'runs':[],
             'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source]},
             'fixture_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
             'bokkio_runtime_integrated':False,'input_dispatched':False}
    def persist(): (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    persist()
    for iteration in range(1,runs+1):
        process=subprocess.Popen([str(executable)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            time.sleep(1)
            image=output/f'owned-window-{iteration}.png'
            try:
                capture=subprocess.run([str(helper),str(process.pid),str(image),fixture.stem],
                                       capture_output=True,text=True,timeout=15)
                row={'run':iteration,'pid':process.pid,'returncode':capture.returncode,
                     'stdout':capture.stdout,'stderr':capture.stderr,'image_exists':image.exists()}
                if capture.returncode==0 and image.is_file():
                    metadata=json.loads(capture.stdout);data=image.read_bytes()
                    width,height=struct.unpack('>II',data[16:24])
                    row.update(metadata=metadata,image_sha256=hashlib.sha256(data).hexdigest(),image_bytes=len(data),
                               passed=data[:8]==b'\x89PNG\r\n\x1a\n' and metadata['pid']==process.pid
                               and (width,height)==(metadata['width'],metadata['height']) and width>0 and height>0)
                else:row['passed']=False
            except subprocess.TimeoutExpired:row={'run':iteration,'pid':process.pid,'error':'capture_timeout','passed':False}
            summary['runs'].append(row);persist();print(json.dumps(row),flush=True)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=10)
    summary['passed']=len(summary['runs'])==runs and all(row['passed'] for row in summary['runs'])
    persist();return summary['passed']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--runs',type=int,choices=[1,3],default=3)
    args=parser.parse_args();raise SystemExit(0 if run(args.fixture,args.output,args.runs) else 1)
