"""Live checks against the disposable Windows interactions fixture.

Run in an unlocked interactive Windows session. --external-input waits for a
key or pointer event from outside Bokkio (a VM console qualifies as simulated
external input; it does not constitute a physical hardware test).
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import statistics
import time


def verify(app, output, external_input=False):
    from bokkio.desktop_control import InputMonitor, guarded_operation, checkpoint
    from bokkio.local_runtime import LocalRuntime
    from bokkio.model import BokkioCompletionUnknown
    from bokkio.sdk import Client
    from bokkio.selector import flatten
    from bokkio.xa11y_backend import Xa11yBackend
    output.mkdir(parents=True, exist_ok=True)
    os.environ['BOKKIO_CONTROL_DIR'] = str(output / 'control')
    b = Xa11yBackend()
    trace = []
    def record(name, **result):
        trace.append({'check': name, **result})
        (output/'checks.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
    full = b.snapshot(app)
    assert {'Bokkio interactions','Bokkio virtual rows'} <= {w['name'] for w in flatten(full['windows']) if w['role']=='window'}
    scope = 'Bokkio interactions'
    expected = {n['name']:n['ref'] for n in flatten(full['windows']) if n['name'] in ('Search','Submit')}
    samples = {'full':[], 'scoped':[]}
    for _ in range(5):
        for key, window in [('full',None),('scoped',scope)]:
            s = b.snapshot(app, window)
            assert s['read']['complete']
            samples[key].append(s['read'])
            if window:
                assert not any(n['name']=='Virtual rows' for n in flatten(s['windows']))
                assert all(next(n['ref'] for n in flatten(s['windows']) if n['name']==name)==ref for name,ref in expected.items())
    record('scope_and_identity', samples=samples,
           median_ms={k:statistics.median(x['elapsed_ms'] for x in v) for k,v in samples.items()})
    c = Client(LocalRuntime(output/'runtime', b)); c.open(apps=[app])
    def observe(**options):
        r=c.call('desktop.observe',{'app':app,'window':scope,**options})
        assert r['status']=='completed',r
        return r['result']
    def arguments(observation, value):
        return {'app':app,'window':scope,'observation_id':observation['observation_id'],
                'ref':expected['Search'],'action':'set_value','value':value}
    partial=observe(read_nodes=8)
    r=c.call('desktop.act',arguments(partial,'must not execute'))
    assert r['dispatched'] is False and r['error_code']=='observation_incomplete',r
    record('partial_write_refused',result=r)
    fresh=observe();r=c.call('desktop.act',arguments(fresh,'Windows native confirmed'))
    assert r['status']=='verified',r
    assert next(n['value'] for n in flatten(b.snapshot(app,scope)['windows']) if n['name']=='Search')=='Windows native confirmed'
    record('native_write_confirmed',status=r['status'])
    monitor=InputMonitor()
    try:
        state=monitor.start();assert state['healthy'],state
        assert monitor.resume()['state']=='ready'
        old=observe()
        # Tagged Bokkio input must not pause its own listener.
        r=c.call('desktop.input',{**arguments(observe(),' tagged'),'action':'type'})
        assert r['status']=='executed' and r['dispatched'],r
        value=next(n['value'] for n in flatten(b.snapshot(app,scope)['windows']) if n['name']=='Search')
        assert ' tagged' in value and 'Windows native confirmed' in value,value
        time.sleep(.3)
        assert monitor.state.status()['state']=='ready',monitor.state.status()
        record('own_tagged_input_ignored',result=r)
        if external_input:
            # Preserve the operation generation across a real listener event.
            with guarded_operation():
                (output/'awaiting-external-input.json').write_text(json.dumps({'state':'ready','timeout_seconds':30}))
                end=time.monotonic()+30
                while monitor.state.status()['state']=='ready' and time.monotonic()<end:time.sleep(.02)
                assert monitor.state.status()['state']=='paused_by_user',monitor.state.status()
                try:checkpoint(dispatched=True)
                except BokkioCompletionUnknown:pass
                else:raise AssertionError('Partial input was not marked unknown')
            r=c.call('desktop.act',arguments(old,'must stay paused'),'paused-operation')
            assert r['dispatched'] is False and r['error_code']=='user_control_paused',r
            time.sleep(.3)
            assert monitor.resume()['state']=='ready'
            stale=c.call('desktop.act',arguments(old,'must require new observation'))
            assert stale['dispatched'] is False and stale['error_code']=='user_control_changed',stale
            r=c.call('desktop.act',arguments(observe(),'resumed once'),'resumed-operation')
            assert r['status']=='verified',r
            cached=c.call('desktop.act',arguments(old,'must stay paused'),'paused-operation')
            assert cached['error_code']=='user_control_paused' and cached['dispatched'] is False,cached
            record('external_takeover_resume_and_unknown',input='external VM console or hardware; record source separately',status='passed')
        else:record('external_takeover',status='not_run')
    finally:monitor.disable()
    (output/'summary.json').write_text(json.dumps({'passed':True,'checks':len(trace),'external_input':external_input},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app',required=True,help='PID of the owned fixture')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--external-input',action='store_true')
    args=parser.parse_args();verify(args.app,args.output,args.external_input)
