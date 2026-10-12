"""Real macOS native/code audit checks, with explicit SQLite/expiry fault injection.

Screen locking and other-display coverage stay separate physical requirements.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from bokkio.audit import identity
from bokkio.runtime import Runtime
from bokkio.sdk import Client


def run(fixture, output):
    if sys.platform != 'darwin':
        raise RuntimeError('Requires the owned macOS native contract fixture')
    output.mkdir(parents=True, exist_ok=False)
    allowed = output / 'allowed'; allowed.mkdir()
    business = output / 'business.json'
    process = subprocess.Popen([str(fixture)], env={**os.environ, 'BOKKIO_NATIVE_RESULT': str(business)},
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {'scope': 'owned_native_code_and_real_sqlite_audit', 'checks': [], 'injected': ['SQLite intent insert rejection', 'approval expiry set into past'],
              'not_tested': ['physical_screen_lock', 'second_display_or_different_scale', 'customer_harness']}
    client = None
    def record(case, passed, **facts):
        report['checks'].append({'case': case, 'passed': bool(passed), **facts})
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    try:
        deadline = time.monotonic() + 10
        while not business.exists() and time.monotonic() < deadline:
            time.sleep(.05)
        if not business.exists(): raise RuntimeError('Native fixture startup failed')
        policy = {'apps': [str(process.pid)], 'paths': [str(allowed)], 'write': True, 'trusted_host': True, 'require_approval': True}
        client = Client(Runtime(output / 'state', policy)); client.open(task_id='macos-audit-contract')
        store = client.runtime.store
        def observe():
            r = client.call('desktop.observe', {'app': str(process.pid)})
            if r['status'] != 'completed': raise RuntimeError(r)
            fields = [n for n in r['result']['nodes'] if n['role'] == 'text_field' and n.get('name') == 'Search']
            if len(fields) != 1: raise RuntimeError('Owned field is not unique')
            return r, fields[0]
        def request(text):
            r, field = observe()
            return {'app': str(process.pid), 'ref': field['ref'], 'observation_id': r['result']['observation_id'], 'action': 'set_value', 'value': text}
        def approved(tool, args, operation):
            pending = client.call(tool, args, operation)
            if pending['status'] != 'approval_required': raise RuntimeError(pending)
            store.decide(pending['approval_id'], 'approved', 'Reviewed owned disposable audit fixture')
            return client.call(tool, args, operation), pending['approval_id']
        outside = output / 'outside.txt'; outside.write_text('owned outside-grant marker')
        denied_app = client.call('desktop.observe', {'app': 'not-granted'})
        denied_path = client.call('evidence.check', {'path': str(outside)})
        record('resource_grants', denied_app['status'] == denied_path['status'] == 'denied' and denied_app['dispatched'] is False and denied_path['dispatched'] is False)
        marker = 'PRIVATE-AUDIT-' + uuid.uuid4().hex
        args = request(marker)
        pending = client.call('desktop.act', args, 'native-approved')
        before = json.loads(business.read_text())['input']
        pending_zero = pending['status'] == 'approval_required' and pending['dispatched'] is False and before == ''
        store.decide(pending['approval_id'], 'approved', 'Reviewed owned native marker')
        done = client.call('desktop.act', args, 'native-approved')
        _, field = observe()
        events = store.query(operation_id='native-approved')
        record('approval_and_native_readback', pending_zero and done['status'] == 'verified' and field['value'] == marker
               and any(e['kind'] == 'approval.approved' and e['data']['actor'] == identity() for e in events), trusted_os_actor=True)
        before_stats = store.stats(client.session_id)
        cached = client.call('desktop.act', args, 'native-approved')
        mismatch = client.call('desktop.act', {**args, 'value': 'different'}, 'native-approved')
        after_stats = store.stats(client.session_id)
        record('idempotency_and_attempt_statistics', cached == done and mismatch['status'] == 'denied'
               and after_stats['logical_operations'] == before_stats['logical_operations']
               and after_stats['known_dispatched'] == before_stats['known_dispatched']
               and after_stats['attempts'] == before_stats['attempts'] + 2
               and after_stats['cached_responses'] == before_stats['cached_responses'] + 1,
               additional_calls=2, additional_dispatches=after_stats['known_dispatched'] - before_stats['known_dispatched'])
        other = Client(Runtime(output / 'state', policy)); other.open()
        other_observe = other.call('desktop.observe', {'app': str(process.pid)})
        cross = client.call('desktop.act', {**args, 'observation_id': other_observe['result']['observation_id']})
        record('cross_session_observation', cross['status'] == 'denied' and cross['dispatched'] is False)
        other.call('session.close')
        code_args = {'code': "print('must not execute')", 'cwd': str(allowed)}
        revoked = client.call('code.run', code_args, 'revoked-code')
        store.decide(revoked['approval_id'], 'approved', 'Owned fixture')
        store.decide(revoked['approval_id'], 'revoked', 'Owned fixture revocation check')
        rejected = client.call('code.run', code_args, 'revoked-code')
        expired = client.call('code.run', code_args, 'expired-code')
        with store.connect() as db:
            db.execute('UPDATE approvals SET expires=0 WHERE id=?', (expired['approval_id'],))
        expiry_poll = client.call('approval.status', {'approval_id': expired['approval_id']})
        expiry_reject = client.call('code.run', code_args, 'expired-code')
        record('revocation_expiry_and_code_hash', rejected['status'] == expiry_reject['status'] == 'denied'
               and rejected['dispatched'] is False and expiry_reject['dispatched'] is False
               and expiry_poll['result'][0]['status'] == 'expired' and mismatch['status'] == 'denied')
        intent_args = request('UNWRITTEN-' + uuid.uuid4().hex)
        initial = client.call('desktop.act', intent_args, 'audit-write-refused')
        store.decide(initial['approval_id'], 'approved', 'Owned SQLite fault injection')
        with store.connect() as db:
            db.execute("CREATE TRIGGER reject_write_intent BEFORE INSERT ON events WHEN NEW.kind='execution.intent' AND json_extract(NEW.data,'$.write')=1 BEGIN SELECT RAISE(FAIL,'owned audit intent rejection'); END")
        try:
            refused = client.call('desktop.act', intent_args, 'audit-write-refused')
        finally:
            with store.connect() as db: db.execute('DROP TRIGGER reject_write_intent')
        _, field = observe()
        record('sqlite_intent_failure_prevents_native_write', refused['dispatched'] is False and field['value'] == marker,
               fault='real SQLite trigger rejection; not a physical disk-full claim')
        code = "from pathlib import Path\nfrom bokkio.sdk import Client\np=Path('owned.csv');p.write_text('key,value\\nfixture,1\\n',encoding='utf-8')\nc=Client.from_environment();r=c.call('evidence.check',{'path':str(p.resolve()),'csv_rows':1});assert r['result']['passed']\nprint(" + repr(marker) + ")"
        queued, approval = approved('code.run', {'code': code, 'cwd': str(allowed)}, 'delegated-code')
        ended = client.wait_job(queued['result']['job_id'], timeout=10)
        artifact = client.call('evidence.check', {'path': str(allowed / 'owned.csv'), 'csv_rows': 1})
        with store.connect() as db:
            linked = db.execute('SELECT operation_id FROM artifacts WHERE id=?', (artifact['result']['artifact']['artifact_id'],)).fetchone()[0]
        audit = store.query(session_id=client.session_id)
        parent = [e for e in audit if e['kind'] == 'request.received' and e['data'].get('parent_operation') == 'delegated-code']
        record('code_artifact_approval_trace', ended['result']['status'] == 'completed' and bool(parent)
               and linked == artifact['operation_id'] and artifact['result']['passed'], delegated_children=len(parent))
        exported = store.export(session_id=client.session_id)
        csv_export = list(csv.DictReader(io.StringIO(store.export('csv', session_id=client.session_id))))
        json_export = [json.loads(line) for line in exported.splitlines()]
        page = store.query(session_id=client.session_id, limit=3)
        tail = store.query(session_id=client.session_id, after=page[-1]['seq'], limit=1000)
        stats = store.stats(client.session_id)
        with store.connect() as db:
            operations = db.execute('SELECT COUNT(*) FROM operations WHERE session_id=?', (client.session_id,)).fetchone()[0]
        record('export_privacy_cursor_and_reconciliation', marker not in exported and marker not in store.export('csv', session_id=client.session_id)
               and len(csv_export) == len(json_export) and page + tail == json_export
               and stats['logical_operations'] == operations
               and stats['attempts'] == sum(e['kind'] in {'request.received','request.cached','request.rejected'} for e in json_export),
               events=len(json_export), logical_operations=operations, attempts=stats['attempts'], cached_responses=stats['cached_responses'])
        read_args = {'artifact_id': artifact['result']['artifact']['artifact_id']}
        read = client.call('artifact.read', read_args, 'private-artifact')
        client.call('session.close')
        late = client.call('artifact.read', read_args, 'private-artifact')
        record('closed_session_cached_artifact_denied', read['status'] == 'completed' and late['status'] == 'denied'
               and late['dispatched'] is False and 'result' not in late)
        report['passed'] = sum(c['passed'] for c in report['checks']); report['total'] = len(report['checks'])
    finally:
        if client and client.session_id: client.call('session.close')
        if process.poll() is None: process.terminate()
        process.wait(timeout=5)
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args(); report=run(args.fixture.resolve(), args.output.resolve())
    print(json.dumps({'passed':report['passed'],'total':report['total'],'report':str(args.output/'report.json')}))
    raise SystemExit(0 if report['passed']==report['total'] else 1)
