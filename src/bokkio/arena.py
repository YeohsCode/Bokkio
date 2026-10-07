"""Stepwise native action transport for Windows Agent Arena runners.

The worker preserves DesktopAgent's planning and recovery state. It cannot
dispatch a native action until the runner consumes that exact action via step().
This is a native action-space extension, not WAA's pyautogui/code_block space.
"""
from __future__ import annotations

import copy
from queue import Empty, Queue
from threading import Event, Thread
import time
from uuid import uuid4

from .model import BokkioError


class NativeArenaAgent:
    action_space = "bokkio_native"

    def __init__(self, backend_factory, agent_factory, apps, trace_path, *, timeout=180):
        self.backend_factory, self.agent_factory = backend_factory, agent_factory
        self.apps, self.trace_path, self.timeout = list(apps), trace_path, timeout
        self._thread = None
        self.reset()

    def reset(self):
        if self._thread is not None and self._thread.is_alive():
            self._cancel.set()
            if self._pending:
                self._pending[1].set()
            self._thread.join(5)
            if self._thread.is_alive():
                raise BokkioError("Native worker is still stopping; cannot start another task")
        self._thread = None
        self._cancel, self._messages = Event(), Queue()
        self._pending = None
        self._instruction = None
        self._terminal = None
        self.trace = None
        self.steps = []

    close = reset

    def _run(self):
        initialized = False
        backend = agent = None
        try:
            import sys
            if sys.platform == "win32":
                import ctypes
                # xa11y uses MTA; its COM supplements must use the same apartment.
                ole32 = ctypes.WinDLL("ole32")
                ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
                ole32.CoInitializeEx.restype = ctypes.c_long
                status = ole32.CoInitializeEx(None, 0)
                if status < 0:
                    raise BokkioError("Could not initialize native worker COM apartment")
                initialized = status in {0, 1}
            backend = self.backend_factory()
            owner = self

            class GatedBackend:
                def snapshot(self, *args, **kwargs):
                    if owner._cancel.is_set():
                        raise BokkioError("Arena task cancelled")
                    return backend.snapshot(*args, **kwargs)

                def windows(self, *args, **kwargs):
                    return backend.windows(*args, **kwargs)

                def perform(self, app, action, **kwargs):
                    request = {"type": "bokkio_native", "token": uuid4().hex,
                               "app": app, "action": action, "arguments": copy.deepcopy(kwargs)}
                    release, reply = Event(), Queue()
                    owner._messages.put(("action", (request, release, reply)))
                    while not release.wait(0.1):
                        if owner._cancel.is_set():
                            raise BokkioError("Arena task cancelled before dispatch")
                    if owner._cancel.is_set():
                        raise BokkioError("Arena task cancelled before dispatch")
                    started = time.monotonic()
                    try:
                        result = backend.perform(app, action, **kwargs)
                    except Exception as error:
                        reply.put((False, str(error), time.monotonic() - started))
                        raise
                    reply.put((True, result, time.monotonic() - started))
                    return result

            agent = self.agent_factory(GatedBackend())
            self.trace = agent.run(self._instruction, self.apps, self.trace_path)
            self._messages.put(("terminal", "DONE" if self.trace["status"] == "completed" else "FAIL"))
        except Exception as error:
            self._messages.put(("error", str(error)))
        finally:
            # Release native UIA/xa11y handles in their own apartment before
            # tearing it down. GatedBackend methods share this backend cell.
            agent = None
            backend = None
            if initialized:
                ole32.CoUninitialize.argtypes = []
                ole32.CoUninitialize.restype = None
                ole32.CoUninitialize()

    def predict(self, instruction, obs):
        """Return exactly one native action, or one terminal sentinel.

        obs is runner metadata. Fresh UIA acquisition stays in the worker, where
        COM objects belong; screenshot/clipboard data cannot authorize actions.
        """
        if self._pending is not None:
            raise BokkioError("Runner must step the pending action before predicting again")
        if self._thread is None:
            self._instruction = instruction
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()
        elif instruction != self._instruction:
            raise BokkioError("Reset before changing the benchmark instruction")
        if self._terminal is not None:
            return [self._terminal]
        try:
            kind, value = self._messages.get(timeout=self.timeout)
        except Empty:
            self._cancel.set()
            raise BokkioError("Arena prediction timed out") from None
        if kind == "error":
            raise BokkioError(value)
        if kind == "terminal":
            self._terminal = value
            return [value]
        self._pending = value
        return [copy.deepcopy(value[0])]

    def step(self, action):
        """Dispatch exactly one previously predicted action and return its receipt."""
        if self._pending is None or action != self._pending[0]:
            raise BokkioError("Unrecognized, altered or replayed native arena action")
        request, release, reply = self._pending
        release.set()
        try:
            passed, result, seconds = reply.get(timeout=self.timeout)
        except Empty:
            self._cancel.set()
            raise BokkioError("Native arena dispatch timed out") from None
        self._pending = None
        receipt = {"step": len(self.steps) + 1, "request": copy.deepcopy(request),
                   "dispatched": True, "passed": passed, "seconds": seconds,
                   "result" if passed else "error": result}
        self.steps.append(receipt)
        return receipt


class WAAAgentAdapter:
    """Four-value predict contract used by the pinned lib_run_single.py.

    The upstream developer guide describes a simpler list interface. The actual
    runner expects response, actions, logs and computer-update arguments.
    """
    action_space = 'bokkio_native'

    def __init__(self, native_agent):
        self.native = native_agent

    def reset(self):
        self.native.reset()

    def predict(self, instruction, obs):
        actions = self.native.predict(instruction, obs)
        return ('Bokkio native UIA step', actions,
                {'native_steps':len(self.native.steps), 'trace_path':str(self.native.trace_path)}, None)


class WAAEnvironmentBridge:
    """Native action-space extension around an upstream-compatible environment.

    Upstream reset/evaluate/observations remain delegated. rebind must create a
    fresh native agent from the allowed apps after environment initialization.
    The original DesktopEnv does not understand these opaque native requests.
    """
    def __init__(self, environment, adapter, rebind):
        self.environment, self.adapter, self.rebind = environment, adapter, rebind

    def __getattr__(self, name):
        return getattr(self.environment, name)

    def reset(self, task_config):
        self.adapter.reset()
        obs = self.environment.reset(task_config=task_config)
        self.adapter.native = self.rebind(task_config, obs)
        self.environment.action_history = []
        return obs

    def step(self, action, pause=0):
        if isinstance(action,str):
            if action not in {'DONE','FAIL'} or action != self.adapter.native._terminal:
                raise BokkioError('Arena terminal must come from native verification')
            receipt={'terminal':action}
            done=True
        else:
            receipt=self.adapter.native.step(action)
            done=False
        self.environment.action_history.append(copy.deepcopy(action))
        if pause:
            time.sleep(min(max(float(pause),0),2))
        return self.environment._get_obs(), 0.0, done, receipt

    def evaluate(self):
        return self.environment.evaluate()
