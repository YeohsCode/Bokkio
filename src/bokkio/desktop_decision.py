"""Desktop Harness local decisions. Jev selects; the model-free Runtime executes."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from urllib.parse import urlparse

from .audit import canonical, digest, identifier, summarize
from .decision import decide
from .execution_context import parent_operation
from .jev import JevProvider, config_path
from .model import BokkioError, BokkioStaleSnapshot, tree_digest
from .runtime import TOOLS
from .tool_schema import APP, SCHEMAS, S, schema, validate

STEP_SCHEMA = schema({**APP, 'goal': S, 'allowed_values': {'type': 'array', 'items': S},
                      'input': schema({k: v for k, v in SCHEMAS['desktop.input']['properties'].items()
                                       if k not in {'app', 'window', 'observation_id', 'ref'}}, ['action'])},
                     ['app', 'window', 'goal'])


def provider_from_environment():
    """Resolve credentials for the configured destination; custom endpoints need their own key."""
    source = os.environ.get('BOKKIO_JEV_SOURCE') or 'openrouter'
    model = os.environ.get('BOKKIO_JEV_MODEL')
    endpoint = os.environ.get('BOKKIO_JEV_API_URL') or JevProvider.ENDPOINTS.get(source)
    from .jev import validate_api_url
    endpoint = validate_api_url(endpoint)
    key = os.environ.get('BOKKIO_JEV_API_KEY')
    if not key:
        path = config_path()
        if path.is_file():
            try:
                private = json.loads(path.read_text(encoding='utf-8'))
                private_endpoint = private.get('api_url') or JevProvider.ENDPOINTS.get(private.get('source', 'openrouter'))
                if private_endpoint == endpoint: key = private.get('api_key')
            except (OSError, ValueError, AttributeError):
                raise BokkioError('Invalid private Jev configuration') from None
    if not key and endpoint == JevProvider.ENDPOINTS['openrouter']:
        key = os.environ.get('OPENROUTER_API_KEY')
        if not key and urlparse(os.environ.get('BOKKIO_PROVIDER_BASE_URL', '')).hostname == 'openrouter.ai':
            key = os.environ.get('BOKKIO_PROVIDER_KEY')
    if not key and endpoint == JevProvider.ENDPOINTS['typesafe']:
        key = os.environ.get('TYPESAFE_API_KEY')
    if not key:
        raise BokkioError('Configure a Jev key for this API URL in Settings')
    return JevProvider(api_key=key, source=source, model=model, api_url=endpoint)


class DesktopDecisionRuntime:
    # Native writes are exposed through the local decision entry. Runtime and saved workflows retain all their tools.
    tools = (TOOLS - {'desktop.act', 'desktop.input', 'desktop.pixel'}) | {'desktop.step'}
    schemas = {'desktop.step': STEP_SCHEMA}
    descriptions = {'desktop.step': 'Delegate ONE native UI action to Jev. Supply a local goal, exact app/window and literal allowed_values; do not choose refs. Jev observes, selects a closed action/target, Runtime executes and reads back. Optional input specifies keys/foreground input; Jev still selects the target. Use the returned operation_id to inspect uncertain completion; never blindly retry.'}

    def __init__(self, runtime, provider_factory=provider_from_environment):
        self.runtime = runtime
        self.provider_factory = provider_factory

    def call(self, tool, arguments=None, *, session_id=None, operation_id=None):
        if tool != 'desktop.step':
            if tool not in self.tools:
                return {'status': 'denied', 'operation_id': operation_id or identifier(), 'dispatched': False,
                        'error': 'Use desktop.step for native UI actions'}
            result = self.runtime.call(tool, arguments, session_id=session_id, operation_id=operation_id)
            if tool == 'capabilities' and result.get('status') == 'completed':
                result = {**result, 'result': {**result['result'], 'tools': sorted(self.tools),
                          'decision_architecture': {'planning': 'Harness SDK', 'native_selection': 'Jev', 'execution': 'Runtime / Driver'}}}
            return result
        return self.step(arguments, session_id, operation_id or identifier())

    def step(self, args, sid, oid):
        runtime = self.runtime
        started = time.monotonic()
        action_result = None
        execution_started = False
        claimed = False
        token = None
        try:
            args = json.loads(canonical(args))
            # Reuse the shared validator without adding a model-dependent tool to Runtime.
            # The local schema is validated explicitly, avoiding mutation of global contracts.
            if not isinstance(args, dict) or set(args) - set(STEP_SCHEMA['properties']) or set(STEP_SCHEMA['required']) - set(args):
                raise ValueError('desktop.step requires app, exact window and goal')
            for field in ('app', 'window', 'goal'):
                if not isinstance(args[field], str) or not args[field].strip(): raise ValueError('Invalid ' + field)
            values = args.get('allowed_values', [])
            if not isinstance(values, list) or len(values) > 64 or any(not isinstance(v, str) or len(v) > 32000 for v in values):
                raise ValueError('allowed_values must be bounded literal strings')
            if len(args['goal']) > 16000: raise ValueError('Local goal exceeds 16000 characters')
            if 'input' in args:
                validate('desktop.input', {'app': args['app'], 'ref': 'pending', 'observation_id': 'pending', **args['input']})
                if set(args['input']) - set(STEP_SCHEMA['properties']['input']['properties']): raise ValueError('Input cannot specify a target')
            scope = runtime._session(sid)
            task = scope.get('task_id')
            request_hash = digest({'tool': 'desktop.step', 'arguments': args, 'session_id': sid})
            with runtime.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT * FROM operations WHERE id=?', (oid,)).fetchone()
                if old:
                    if old['hash'] != request_hash: raise ValueError('operation_id request mismatch')
                    runtime.store.emit('request.cached', session_id=sid, operation_id=oid,
                                       data={'tool': 'desktop.step', 'dispatched_this_attempt': False}, db=db)
                    return json.loads(old['result']) if old['result'] else {'status': 'completion_unknown', 'operation_id': oid,
                        'session_id': sid, 'dispatched': 'unknown', 'error': 'Step already claimed; inspect child operations before retrying'}
                db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?)',
                           (oid, sid, 'desktop.step', request_hash, canonical(args), 'running', None, time.time()))
                runtime.store.emit('request.received', session_id=sid, operation_id=oid,
                                   data={'tool': 'desktop.step', 'input': summarize(args), 'task_id': task,
                                         'parent_operation': parent_operation.get()}, db=db)
            claimed = True
            token = parent_operation.set(oid)
            provider = self.provider_factory()
            target = {k: args[k] for k in ('app', 'window')}
            def observe():
                response = runtime.call('desktop.observe', {**target, 'max_nodes': 120, 'max_bytes': 100000}, session_id=sid)
                if response['status'] != 'completed': raise BokkioError(response.get('error', 'Observation failed'))
                observation = runtime._get_observation(sid, response['result']['observation_id'])
                return response, observation['snapshot']
            before, snapshot = observe()
            snapshot = {**snapshot, 'window_filter': args['window']}
            def event(kind, data):
                runtime.store.emit(kind, session_id=sid, operation_id=oid, data=data)
            class LoggedProvider:
                def ask(self, state, questions):
                    runtime._session(sid)
                    event('decision.requested', {'engine': 'Jev', 'model': getattr(provider, 'model', 'Jev'),
                                                'source': getattr(provider, 'source', 'unknown'), 'questions': list(questions)})
                    result = provider.ask(state, questions)
                    runtime._session(sid)
                    event('decision.returned', {'engine': 'Jev', 'model': result.get('model', getattr(provider, 'model', 'Jev')),
                                               'duration_ms': round(result.get('elapsed_seconds', 0) * 1000, 3)})
                    return result
            decision, response = decide(LoggedProvider(), args['goal'], snapshot, values, allow_done=False,
                                        require_action=True, inputs=[args['input']] if 'input' in args else ())
            event('decision.selected', {'engine': 'Jev', 'action': decision.input['action'] if decision.input else decision.action,
                                       'ref': decision.ref, 'confidence': decision.confidence, 'snapshot_sha256': decision.snapshot_id})
            # Model latency can exceed the observation TTL. Reobserve and bind the *same* semantic tree to a fresh ID.
            fresh, fresh_snapshot = observe()
            if tree_digest(fresh_snapshot['windows']) != decision.snapshot_id:
                raise BokkioStaleSnapshot('UI changed while Jev was deciding; observe and decide again')
            action_args = {**target, 'observation_id': fresh['result']['observation_id'], 'ref': decision.ref}
            if decision.input:
                action_tool = 'desktop.input'
                action_args.update(decision.input)
            else:
                action_tool = 'desktop.act'
                action_args.update(action=decision.action)
                action_args.update({k: v for k in ('value', 'direction', 'amount') if (v := getattr(decision, k)) is not None})
            execution_started = True
            action_result = runtime.call(action_tool, action_args, session_id=sid)
            result = {**action_result, 'operation_id': oid, 'session_id': sid,
                      'result': {'decision': {'engine': 'Jev', 'action': action_args['action'], 'ref': decision.ref,
                                               'confidence': decision.confidence}, 'execution': action_result}}
            if action_result['status'] in {'executed', 'verified', 'completed'}:
                # This is execution evidence; the planner evaluates the task outcome from the actual readback.
                readback = runtime.call('desktop.observe', {**target, 'max_nodes': 60, 'max_bytes': 16000}, session_id=sid)
                result['result']['readback'] = readback
                if readback['status'] != 'completed':
                    result.update(status='failed', error='Action returned but readback failed; inspect execution before another action')
            event('decision.finished', {'status': result['status'], 'dispatched': result.get('dispatched')})
        except Exception as error:
            result = {'status': 'completion_unknown' if execution_started and action_result is None else 'failed' if claimed else 'denied', 'operation_id': oid, 'session_id': sid,
                      'dispatched': action_result.get('dispatched') if action_result else 'unknown' if execution_started else False,
                      'error': str(error), 'error_type': type(error).__name__}
            if action_result: result['result'] = {'execution': action_result}
            if claimed:
                runtime.store.emit('decision.failed', session_id=sid, operation_id=oid,
                                   data={'engine': 'Jev', 'status': result['status'], 'error_type': type(error).__name__})
        finally:
            if token is not None: parent_operation.reset(token)
        return runtime._finish('desktop.step', sid, oid, result, started) if claimed else result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True)
    args = parser.parse_args()
    from .local_runtime import LocalRuntime
    from .mcp_server import serve
    asyncio.run(serve(DesktopDecisionRuntime(LocalRuntime(args.state))))


if __name__ == '__main__':
    main()
