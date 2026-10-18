"""Same-user cooperative desktop pause, shared across Runtime processes.

This does not suppress physical input, authorize code, or cancel an in-flight
native call. Only the local UI/CLI can configure/resume it; MCP exposes status.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import uuid

from .model import BokkioActionRefused, BokkioCompletionUnknown

EVENT_TAG = 0x424B494F
current_control = ContextVar('bokkio_control', default=None)


def validate_state(data):
    if (not isinstance(data, dict)
            or any(type(data.get(k)) is not bool for k in ('enabled', 'paused'))
            or any(type(data.get(k)) is not int or data[k] < 0 for k in ('generation', 'held'))
            or any(type(data.get(k)) not in (int, float) or not math.isfinite(data[k]) or data[k] < 0
                   for k in ('heartbeat', 'resume_after'))):
        raise ValueError('Invalid desktop control state')
    return data


def directory():
    return Path(os.environ.get('BOKKIO_CONTROL_DIR') or
                str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / '.bokkio' / 'control'))


class ControlState:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else directory()
        self.path = self.root / 'state.sqlite'

    @contextmanager
    def transaction(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with sqlite3.connect(self.path, timeout=1) as db:
            db.execute('CREATE TABLE IF NOT EXISTS control (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM control WHERE id=1').fetchone()
            data = json.loads(row[0]) if row else {'enabled': False, 'generation': 0, 'heartbeat': 0,
                                                  'paused': False, 'held': 0, 'resume_after': 0}
            validate_state(data)
            yield data
            db.execute('INSERT OR REPLACE INTO control VALUES(1,?)', (json.dumps(data),))

    def status(self):
        if not self.path.exists():
            return {'enabled': False, 'state': 'disabled', 'generation': 0}
        try:
            with sqlite3.connect(self.path, timeout=1) as db:
                row = db.execute('SELECT data FROM control WHERE id=1').fetchone()
            data = validate_state(json.loads(row[0]) if row else None)
        except (sqlite3.Error, ValueError, TypeError):
            return {'enabled': True, 'state': 'unavailable', 'generation': None, 'healthy': False}
        healthy = 0 <= time.monotonic() - data.get('heartbeat', 0) < 2
        state = ('disabled' if not data['enabled'] else 'unavailable' if not healthy or data.get('error')
                 else 'paused_by_user' if data['paused'] else 'ready')
        return {k: v for k, v in {**data, 'state': state, 'healthy': healthy}.items()
                if k not in {'monitor_token'}}

    def configure(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('enabled must be boolean')
        with self.transaction() as data:
            data.update(enabled=enabled, generation=data['generation'] + 1)
            if enabled:
                data.update(paused=True, resume_after=0, resume_request=None)
        return self.status()

    def heartbeat(self, *, held=0, error=None):
        with self.transaction() as data:
            data.update(heartbeat=time.monotonic(), held=held, error=error)

    def event(self, kind, stamp=None):
        stamp = time.monotonic() if stamp is None else stamp
        with self.transaction() as data:
            if not data['enabled'] or stamp <= data.get('resume_after', 0):
                return
            data.update(paused=True, generation=data['generation'] + 1,
                        last_user_event=stamp, last_event_kind=kind)

    def resume(self):
        with self.transaction() as data:
            if not data['enabled']:
                raise ValueError('Enable user takeover first')
            if data.get('error') or not 0 <= time.monotonic() - data['heartbeat'] < 2:
                raise ValueError('Input monitor is unavailable; desktop writes remain paused')
            if data.get('held'):
                raise ValueError('Release physical keys and buttons before continuing')
            data.update(paused=False, generation=data['generation'] + 1, resume_after=time.monotonic())
        return self.status()

    def request_resume(self):
        request = uuid.uuid4().hex
        with self.transaction() as data:
            if not data['enabled']:
                raise ValueError('Enable user takeover first')
            data.update(paused=True, generation=data['generation'] + 1,
                        resume_request=request, resume_error=None)
        return request

    def acknowledge_resume(self, held):
        # Only the listener calls this, after consuming the pending input queue.
        with self.transaction() as data:
            request = data.get('resume_request')
            if not request:
                return
            error = ('Input monitor is unavailable; desktop writes remain paused'
                     if not data['enabled'] or data.get('error')
                     or not 0 <= time.monotonic() - data['heartbeat'] < 2 else
                     'Release physical keys and buttons before continuing' if held else None)
            data.update(paused=bool(error), held=len(held), resume_request=None,
                        resume_ack=request, resume_error=error,
                        generation=data['generation'] + 1, resume_after=time.monotonic())

    def check(self, expected=None):
        state = self.status()
        if not state['enabled']:
            # An already enabled operation must not survive a configuration change.
            if expected is not None:
                raise BokkioActionRefused('Desktop control changed; reobserve before input', 'user_control_changed')
            return None
        if state['state'] != 'ready' or expected is not None and state['generation'] != expected:
            raise BokkioActionRefused('Desktop task paused: ' + state['state'], 'user_control_paused')
        return state['generation']


@contextmanager
def guarded_operation():
    existing = current_control.get()
    if existing is not None:
        checkpoint()
        yield
        return
    state = ControlState()
    generation = state.check()
    token = current_control.set((state, generation))
    try:
        yield
    finally:
        current_control.reset(token)


def checkpoint(dispatched=False):
    context = current_control.get()
    state, generation = context if context is not None else (ControlState(), None)
    try:
        if context is not None and generation is None and state.status()['enabled']:
            raise BokkioActionRefused('Desktop control changed during the operation', 'user_control_changed')
        state.check(generation)
    except BokkioActionRefused as error:
        if dispatched:
            raise BokkioCompletionUnknown('User takeover after partial input; inspect before retry') from error
        raise


def native_guard():
    context = current_control.get()
    if context is None:
        return {}
    state, generation = context
    if generation is None:
        return {}
    # Atomic JSON replacement gives native helpers an inexpensive per-event check.
    return {'control_file': str(state.root / 'guard.json'), 'control_generation': generation}


def publish_guard(state, held=()):
    value = state.status()
    target = state.root / 'guard.json'
    temporary = state.root / ('guard-' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps({'allowed': value['state'] == 'ready',
                                     'enabled': value['enabled'], 'generation': value['generation'],
                                     'physical_held': sorted(held), 'expires': time.time() + 1.5}))
    os.replace(temporary, target)


class InputMonitor:
    def __init__(self, root=None):
        self.state = ControlState(root)
        self.process = None

    def start(self):
        self.state.configure(True)
        publish_guard(self.state)
        if self.state.status().get('healthy') and not self.state.status().get('error'):
            return self.state.status()
        self.process = subprocess.Popen([sys.executable, '-m', 'bokkio.input_monitor', '--directory', str(self.state.root)],
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}))
        end = time.monotonic() + 3
        while time.monotonic() < end:
            state = self.state.status()
            if state.get('healthy') or self.process.poll() is not None:
                return state
            time.sleep(.02)
        return self.state.status()

    def disable(self):
        result = self.state.configure(False)
        publish_guard(self.state)
        return result

    def resume(self):
        request = self.state.request_resume()
        end = time.monotonic() + 1
        while time.monotonic() < end:
            result = self.state.status()
            if result.get('resume_ack') == request:
                if result.get('resume_error'):
                    raise ValueError(result['resume_error'])
                return result
            time.sleep(.02)
        with self.state.transaction() as data:
            if data.get('resume_request') == request or data.get('resume_ack') == request:
                data.update(paused=True, resume_request=None, generation=data['generation'] + 1)
        raise ValueError('Input monitor did not confirm resume; desktop writes remain paused')


def physically_held(item):
    context = current_control.get()
    state = context[0] if context else ControlState()
    if not state.status()['enabled']:
        return False
    try:
        value = json.loads((state.root / 'guard.json').read_text())
        if value['expires'] < time.time():
            return True
        return item in value.get('physical_held', [])
    except (OSError, ValueError, KeyError):
        return True


def windows_move(user, x, y, dispatched=False):
    """Use tagged absolute input when monitoring; SetCursorPos has no event tag."""
    checkpoint(dispatched)
    if not ControlState().status()['enabled']:
        return bool(user.SetCursorPos(x, y))
    import ctypes as c
    from ctypes import wintypes as w
    class Mouse(c.Structure):
        _fields_ = [('dx', w.LONG), ('dy', w.LONG), ('data', w.DWORD), ('flags', w.DWORD),
                    ('time', w.DWORD), ('extra', c.c_size_t)]
    class Keyboard(c.Structure):
        _fields_ = [('vk', w.WORD), ('scan', w.WORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', c.c_size_t)]
    class Union(c.Union):
        _fields_ = [('mouse', Mouse), ('keyboard', Keyboard)]
    class Input(c.Structure):
        _fields_ = [('type', w.DWORD), ('data', Union)]
    left, top, width, height = (user.GetSystemMetrics(i) for i in (76, 77, 78, 79))
    if width <= 1 or height <= 1:
        raise BokkioActionRefused('Virtual desktop geometry is unavailable')
    event = Input(0, Union(mouse=Mouse(round((x-left)*65535/(width-1)),
                                      round((y-top)*65535/(height-1)), 0, 0xC001, 0, EVENT_TAG)))
    # Avoid replacing the SendInput signature used by the caller's own Input type.
    send = c.WINFUNCTYPE(w.UINT, w.UINT, c.c_void_p, c.c_int)(('SendInput', user))
    if send(1, c.byref(event), c.sizeof(Input)) != 1:
        raise BokkioCompletionUnknown('Pointer dispatch could not be confirmed')
    return True
