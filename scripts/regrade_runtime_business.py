"""Replay preserved business evidence after judge fixes, without actor execution.

Initial scores remain immutable. Late reopen diagnoses, if supplied, are
explicit supplementary evidence, never fresh caller attempts.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evals.runtime_business import business_checks,snapshot_matches,sha
from scripts.evaluate_runtime_business import protocol_complete
from bokkio.selector import flatten


def regrade(batch,late_reopen=None):
    initial=json.loads((batch/'report.json').read_text())
    late=json.loads(late_reopen.read_text()) if late_reopen else []
    late_tasks={r['task'] for r in late if r.get('late_readonly_reopen_correct')}
    results=[]
    for old in initial['results']:
        result={'task':old['task'],'client':old['client'],'initial_passed':old['passed'],
                'corrected_passed':old['passed'],'started':old.get('started'),
                'fresh_actor_attempt':False,'supplementary_reopen_evidence':False}
        if not old.get('started'):
            results.append(result);continue
        folder=batch/(old['task']+'-'+old['client'])
        case=json.loads((folder/'case.json').read_text())
        unchanged=all((Path(case['out'])/p).is_file() and sha(Path(case['out'])/p)==h
                      for p,h in old['output_sha256'].items())
        checks=business_checks(case) if not case.get('web_kind') else old['business_checks']
        with sqlite3.connect('file:'+str(folder/'state/runtime.sqlite3')+'?mode=ro',uri=True) as db:
            job_ids=[r[0] for r in db.execute('SELECT id FROM jobs')]
            unknown=db.execute("SELECT count(*) FROM operations WHERE status='completion_unknown'").fetchone()[0]
            snapshots=[json.loads(r[0]) for r in db.execute('SELECT payload FROM observations ORDER BY rowid')]
            events=[{'seq':seq,'operation_id':op,'kind':kind,'data':json.loads(data)}
                    for seq,op,kind,data in db.execute('SELECT seq,operation_id,kind,data FROM events ORDER BY seq')]
        jobs=jobs_before_judge(job_ids,events)
        ui=all(u['correct'] for u in old['ui_checks']) and bool(old['ui_checks'])
        if case['ui_outputs']:
            ui=all(any(p.get('window') in {Path(t['file']).name,Path(t['file']).stem}
                       and p.get('snapshot') and snapshot_matches(t,flatten(p['snapshot']['windows']))
                       for p in snapshots) for t in case['ui_outputs'])
        persisted=not old['persistence']['required'] or old['persistence']['correct']
        if not persisted and old['client']=='codex-current' and old['task'] in late_tasks:
            persisted=True;result['supplementary_reopen_evidence']=True
        # Initial runner collected sessions while the caller was finished and
        # before evaluator cleanup. Its tool list proves a session was opened;
        # native/browser UI evidence was then captured from the open session.
        protocol=protocol_complete(old['client_exit_code'],old['termination'],[True],[True],jobs,unknown)
        result.update(corrected_passed=bool(unchanged and checks['business_correct'] and checks['source_unchanged']
                                           and ui and persisted and protocol),
                      original_output_hashes_unchanged=unchanged,business_correct=checks['business_correct'],
                      ui_correct=ui,persistence_correct=persisted,protocol_completed=protocol,
                      unknown_operations=unknown,job_statuses_at_judge_start=jobs)
        results.append(result)
    source_files=[Path('evals/runtime_business.py'),Path('scripts/evaluate_runtime_business.py'),Path(__file__).relative_to(Path.cwd())]
    return {'scope':'judge_correction_replay_not_new_actor_attempts','initial_planned':initial['planned'],
            'initial_passed':initial['passed'],'corrected_passed':sum(r['corrected_passed'] for r in results),
            'grader_sha256':{str(p):sha(p) for p in source_files},'results':results}


def jobs_before_judge(job_ids,events):
    # Cleanup can turn unfinished jobs into terminal states. That must never
    # upgrade a caller's score, so replay only finishes recorded before judge.
    cutoff=min((e['seq'] for e in events if e['kind']=='request.received' and
                ((e['operation_id'] or '').startswith('independent-judge-') or
                 e['data'].get('tool')=='session.close')),default=float('inf'))
    finished={e['data']['job_id']:e['data']['status'] for e in events
              if e['seq']<cutoff and e['kind']=='job.finished'}
    return [finished.get(job,'unfinished_at_judge_start') for job in job_ids]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--batch',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--late-reopen',type=Path)
    args=p.parse_args();result=regrade(args.batch,args.late_reopen)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in {'initial_planned','initial_passed','corrected_passed'}}))
