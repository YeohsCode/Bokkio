"""Passive input monitor. Hook callbacks enqueue metadata and return immediately."""
from __future__ import annotations

import argparse
import ctypes as c
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

from .desktop_control import ControlState, EVENT_TAG, publish_guard


def mouse_held(message, data=0):
    buttons = {0x201: (1, True), 0x202: (1, False), 0x204: (2, True),
               0x205: (2, False), 0x207: (3, True), 0x208: (3, False)}
    if message in (0x20B, 0x20C):
        button = (data >> 16) & 0xffff
        return ('mouse:' + str(3 + button), message == 0x20B) if button in (1, 2) else None
    item = buttons.get(message)
    return ('mouse:' + str(item[0]), item[1]) if item else None


def windows_events(events, stopped):
    from ctypes import wintypes as w
    user, kernel = c.WinDLL('user32', use_last_error=True), c.WinDLL('kernel32', use_last_error=True)
    class Mouse(c.Structure):
        _fields_ = [('pt', w.POINT), ('data', w.DWORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', c.c_size_t)]
    class Key(c.Structure):
        _fields_ = [('vk', w.DWORD), ('scan', w.DWORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', c.c_size_t)]
    callback = c.WINFUNCTYPE(c.c_ssize_t, c.c_int, w.WPARAM, w.LPARAM)
    user.CallNextHookEx.argtypes = [w.HHOOK, c.c_int, w.WPARAM, w.LPARAM]
    user.CallNextHookEx.restype = c.c_ssize_t
    user.SetWindowsHookExW.argtypes = [c.c_int, callback, w.HINSTANCE, w.DWORD]
    user.SetWindowsHookExW.restype = w.HHOOK
    user.UnhookWindowsHookEx.argtypes = [w.HHOOK]
    kernel.GetModuleHandleW.restype = w.HMODULE
    def put(kind, held=None, point=None):
        try:
            events.put_nowait({'kind': kind, 'held': held, 'point': point, 'stamp': time.monotonic()})
        except queue.Full:
            stopped.set()
    @callback
    def mouse(code, message, data):
        if code >= 0:
            item = c.cast(data, c.POINTER(Mouse)).contents
            if item.extra != EVENT_TAG:
                kind = 'move' if message == 0x200 else 'mouse'
                held = mouse_held(message, item.data)
                put(kind, held, [item.pt.x, item.pt.y])
        return user.CallNextHookEx(None, code, message, data)
    @callback
    def keyboard(code, message, data):
        if code >= 0:
            item = c.cast(data, c.POINTER(Key)).contents
            if item.extra != EVENT_TAG:
                put('key', None if item.vk in (0xE5, 0xF3, 0xF4) else
                    ('key:' + str(item.vk), message in (0x100, 0x104)))
        return user.CallNextHookEx(None, code, message, data)
    hooks = []
    try:
        def install():
            new = [user.SetWindowsHookExW(14, mouse, kernel.GetModuleHandleW(None), 0),
                   user.SetWindowsHookExW(13, keyboard, kernel.GetModuleHandleW(None), 0)]
            if not all(new):
                for hook in new:
                    if hook: user.UnhookWindowsHookEx(hook)
                raise OSError('Input hooks could not be installed')
            return new
        hooks = install()
        point=w.POINT();user.GetCursorPos(c.byref(point))
        for vk, button in ((1, 1), (2, 2), (4, 3), (5, 4), (6, 5)):
            if user.GetAsyncKeyState(vk)&0x8000:
                put('initial', ('mouse:'+str(button), True))
        for vk in range(8,255):
            # Side-specific modifiers are already sampled; generic aliases can
            # otherwise remain held after their side-specific key-up arrives.
            if vk not in (0x10,0x11,0x12,0xE5,0xF3,0xF4) and user.GetAsyncKeyState(vk)&0x8000:
                put('initial', ('key:'+str(vk),True))
        put('ready', point=[point.x,point.y])
        msg = w.MSG()
        last_rotation = time.monotonic()
        last_beat = 0
        while not stopped.is_set():
            while user.PeekMessageW(c.byref(msg), None, 0, 0, 1):
                user.TranslateMessage(c.byref(msg)); user.DispatchMessageW(c.byref(msg))
            # Windows may remove a stalled hook without notification; renew periodically.
            if time.monotonic() - last_rotation > 10:
                new = install()
                for hook in hooks: user.UnhookWindowsHookEx(hook)
                hooks = new; last_rotation = time.monotonic()
            if time.monotonic() - last_beat > .25:
                put('heartbeat'); last_beat = time.monotonic()
            time.sleep(.005)
    finally:
        for hook in hooks: user.UnhookWindowsHookEx(hook)


def run(root):
    state = ControlState(root)
    # Only one monitor owns this OS-user directory, across all MCP/Desktop instances.
    lock = (root / 'monitor.lock').open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            lock.write(b'0'); lock.flush(); lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close(); return
    events, stopped = queue.Queue(maxsize=2048), threading.Event()
    child = None
    def listen():
        nonlocal child
        try:
            if sys.platform == 'win32':
                windows_events(events, stopped)
            elif sys.platform == 'darwin':
                from .app_launch import native_helper
                child = subprocess.Popen([str(native_helper('macos_control'))], stdout=subprocess.PIPE, text=True)
                for line in child.stdout:
                    data = json.loads(line)
                    data.setdefault('stamp', time.monotonic())
                    events.put_nowait(data)
                raise RuntimeError('Input listener ended')
            else:
                raise RuntimeError('User takeover needs Windows or macOS')
        except Exception as error:
            try: events.put_nowait({'kind': 'error', 'error': str(error)})
            except queue.Full: pass
            stopped.set()
    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    held, last_point, distance, last_move = set(), None, 0.0, 0.0
    ready, last_beat = False, time.monotonic()
    last_publish = 0
    try:
        while state.status()['enabled']:
            error = None
            changed = False
            for _ in range(2048):
                try: event = events.get_nowait()
                except queue.Empty: break
                kind = event['kind']
                if kind == 'error':
                    error = event.get('error', 'Input monitoring unavailable'); break
                last_beat = event.get('stamp', time.monotonic())
                if kind == 'ready':
                    ready = True;held.update(event.get('physical_held',[]))
                    last_point=event.get('point');changed=True;continue
                if kind == 'heartbeat': continue
                if kind == 'released': held.clear(); changed=True; continue
                item = event.get('held')
                if item:
                    changed = True
                    if item[1]: held.add(item[0])
                    else: held.discard(item[0])
                if kind == 'initial':continue
                point, stamp = event.get('point'), event.get('stamp', time.monotonic())
                if kind == 'move':
                    if point is None: continue
                    if stamp - last_move > .5: distance = 0
                    if last_point is not None:
                        distance += ((point[0]-last_point[0])**2 + (point[1]-last_point[1])**2)**.5
                    last_point, last_move = point, stamp
                    if distance < 8: continue
                    distance = 0
                state.event(kind, stamp)
                changed = True
            if stopped.is_set() or not thread.is_alive(): error = error or 'Input monitor stopped'
            if ready and time.monotonic() - last_beat > 1:
                error = error or 'Input listener heartbeat expired'
            pending = state.status().get('resume_request')
            if (ready or error) and (changed or error or pending or time.monotonic() - last_publish >= .2):
                state.heartbeat(held=len(held), error=error)
                if ready and not error and events.empty():
                    state.acknowledge_resume(held)
                publish_guard(state, held)
                last_publish = time.monotonic()
            if error: return
            time.sleep(.02)
    finally:
        stopped.set()
        if child: child.terminate()
        state.heartbeat(error='Input monitor stopped')
        publish_guard(state)
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    run(parser.parse_args().directory)
