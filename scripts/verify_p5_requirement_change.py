"""Real Planner/Jev/native test: revise a delivered count, preserve both versions."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import time

from bokkio.agent import DesktopAgent
from bokkio.jev import JevProvider
from bokkio.planner import OpenRouterPlanner
from bokkio.selector import flatten
from bokkio.xa11y_backend import Xa11yBackend
from verify_waa_longchain import adapted_goal, checks_from_trace, save
from waa_variations import prepare_variant, evaluate_variant


def delivery_for(path):
    def verify(_):
        exists = path.is_file()
        info = {'path':str(path), 'exists':exists}
        if exists:
            data = path.read_bytes()
            info.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        return exists, {'required_files':[info]}
    return verify


def reopen(path, output, owned):
    import xa11y
    if not path.is_file():
        return False
    before = path.read_bytes()
    process = subprocess.Popen(['notepad.exe', str(path)]); owned.append(process)
    xa11y.App.by_pid(process.pid, timeout=20)
    snapshot = Xa11yBackend().snapshot(str(process.pid))
    save(output, snapshot)
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    passed = any(n['role']=='text_area' and isinstance(n['value'],str)
                 and n['value'].replace('\r\n','\n')==text for n in flatten(snapshot['windows']))
    process.terminate(); process.wait(timeout=10)
    return passed and path.read_bytes()==before


def run(output):
    import xa11y
    output.mkdir(parents=True, exist_ok=False)
    folders = {name:output/name for name in ['Documents','Pictures','Downloads','Desktop']}
    for folder in folders.values(): folder.mkdir()
    source = folders['Documents']
    inputs, instruction, expected = prepare_variant('count-punctuation', source)
    source_hash = hashlib.sha256(inputs[0].read_bytes()).hexdigest()
    artifacts = [source/'count-v1.txt', source/'count-v2.txt']
    backend = Xa11yBackend(); planner = OpenRouterPlanner(reasoning_effort='low')
    source_hashes={name:hashlib.sha256(Path(importlib.import_module(name).__file__).read_bytes()).hexdigest()
                   for name in ['bokkio.agent','bokkio.planner','bokkio.decision','bokkio.xa11y_backend','bokkio.jev','bokkio.windows_uia']}
    save(output/'selection.json', {'scope':'native_requirement_change_development_run',
         'selected_before_execution':True, 'versions':[{'case_insensitive':True,'expected':'7'},
         {'case_insensitive':False,'expected':'5'}], 'python':platform.python_version(),
         'max_actions':40,'max_replans':3,'max_phases':8,'planner_model':planner.model,
         'source_hashes':source_hashes,
         'harness_hashes':{name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                            for name in ['verify_p5_requirement_change.py','verify_waa_longchain.py','waa_variations.py']}})
    save(output/'setup.json', {'source':str(inputs[0]), 'source_sha256':source_hash,
                               'artifacts':[str(p) for p in artifacts]})
    owned=[]; results=[]; trace={}; started=time.perf_counter()
    summary={'planned':2,'attempted':0,'passed':0,'versions':results}
    save(output/'summary.json',summary)
    try:
        note = subprocess.Popen(['notepad.exe']); owned.append(note)
        xa11y.App.by_pid(note.pid,timeout=30); apps=[str(note.pid)]
        save(output/'initial.json',backend.snapshot(apps[0]))
        for index, artifact in enumerate(artifacts, 1):
            if index == 2:
                instruction = ('Reopen the original input "largefile.txt" from the Documents folder in Notepad. '
                    'The requirement has changed: count the word "example" as a whole word, '
                    'CASE-SENSITIVELY, matching lowercase example only. Punctuation separates words, '
                    'substrings do not count. Write only the decimal count. '
                    f'Keep the previously delivered file "{artifacts[0]}" unchanged. '
                    'Save this revised deliverable as a separate new file.')
                expected = '5'
            goal = adapted_goal(instruction, folders, inputs, artifact)
            save(output/f'goal-v{index}.json', {'goal':goal})
            agent = DesktopAgent(backend,planner,JevProvider(),max_actions=40,max_replans=3,
                                 max_phases=8,final_verifier=delivery_for(artifact),required_sources=[str(inputs[0])])
            trace = agent.run(goal,apps,output/'trace.json',
                resume=output/'v1-trace.json' if index==2 else None,
                amend_reason='User requested case-sensitive matching and a separate output version' if index==2 else None)
            save(output/f'v{index}-trace.json',trace)
            # Each revision must independently prove source acquisition and Save As.
            revision_trace={'events':[e for e in trace['events'] if e.get('goal_revision',1)==index]}
            checks=checks_from_trace(revision_trace,source,artifact,'word-count',inputs)
            checks.update(independent_content=evaluate_variant('word-count',artifact,expected),
                          input_bytes_preserved=hashlib.sha256(inputs[0].read_bytes()).hexdigest()==source_hash,
                          fresh_native_reopen=reopen(artifact,output/f'reopened-v{index}.json',owned))
            if index==2:
                first=json.loads((output/'v1-trace.json').read_text())
                checks.update(previous_history_preserved=trace['events'][:len(first['events'])]==first['events'],
                              requirement_revision=trace['goal_revision']==2,
                              old_output_preserved=artifacts[0].read_bytes()==first_bytes,
                              two_artifact_versions=len(trace['artifact_versions'])==2)
            row={'revision':index,'agent_status':trace['status'],'actions':trace['actions'],
                 'replans':trace['replans'],'phases':trace['phases'],'checks':checks,
                 'passed':trace['status']=='completed' and all(checks.values())}
            if artifact.is_file():
                row['artifact_sha256']=hashlib.sha256(artifact.read_bytes()).hexdigest()
            results.append(row); summary.update(attempted=len(results),passed=sum(r['passed'] for r in results))
            save(output/'summary.json',summary); print(json.dumps(row),flush=True)
            if index==1:
                if not row['passed']: break
                first_bytes=artifact.read_bytes()
    except Exception as error:
        summary['error']=str(error)
    finally:
        for process in owned:
            if process.poll() is None: process.terminate(); process.wait(timeout=10)
        summary['seconds']=round(time.perf_counter()-started,3)
        save(output/'summary.json',summary)
        (output/'done').write_text('done',encoding='utf-8')
    return summary['passed']==summary['planned'] and 'error' not in summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(0 if run(parser.parse_args().output) else 1)
