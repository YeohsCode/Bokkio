"""Reproduce specific Python behavior without Windows, network, models or GUI input.

Third-party functions are compiled from their original AST with decorators/imports
omitted. OS dependencies are replaced by explicit stubs. This is not a Windows
integration test, performance comparison or task-success benchmark.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as N


def source_function(path, name):
    matches = [n for n in ast.walk(ast.parse(path.read_text()))
               if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(matches) == 1, (path, name)
    return copy.deepcopy(matches[0])


def compile_functions(path, names, environment):
    nodes = [source_function(path, name) for name in names]
    for node in nodes:
        node.decorator_list = []
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), environment)
    return environment


def run(windows_source, root):
    results = []
    source = windows_source / 'src/windows_mcp'
    service = source / 'desktop/service.py'
    snapshot = source_function(source / 'tools/snapshot.py', '_state_tool')
    defaults = dict(zip([a.arg for a in snapshot.args.args][-len(snapshot.args.defaults):],
                        [ast.literal_eval(n) for n in snapshot.args.defaults]))
    assert defaults['use_vision'] is False and defaults['use_ui_tree'] is True
    results.append({'id': 'P1', 'fact': 'Snapshot defaults to UI tree without screenshot',
                    'defaults': defaults})

    def no_capture(*args, **kwargs):
        raise AssertionError('screenshot path was called')

    env = {'time': time.time, 'perf_counter': time.perf_counter,
           '_snapshot_profile_enabled': lambda: False,
           'get_current_desktop': lambda: {}, 'get_all_desktops': lambda: [],
           'DesktopState': N, 'logger': logging.getLogger('review')}
    state_function = compile_functions(service, ['get_state'], env)['get_state']
    desktop = N(get_displays=lambda: [], parse_region_selection=lambda _: None,
                get_controls_handles=lambda: set(), get_windows=lambda **_: ([], set()),
                get_active_window=lambda **_: None, get_cursor_location=lambda: (0, 0),
                tree=N(get_state=lambda *a, **kw: N()),
                get_screenshot=no_capture, get_annotated_screenshot=no_capture)
    state = state_function(desktop)
    assert state.screenshot is None
    results.append({'id': 'P2', 'fact': 'Desktop.get_state default did not call either capture function',
                    'scope': 'Original Python method; OS/window/tree dependencies stubbed'})

    env = compile_functions(service, ['get_coordinates_from_label'], {})
    desktop = N(desktop_state=N(tree_state=N(interactive_nodes=[N(center=N(x=100, y=200))],
                                             scrollable_nodes=[])))
    desktop.get_coordinates_from_label = lambda label: env['get_coordinates_from_label'](desktop, label)
    clicks = []
    desktop.click = lambda **kw: clicks.append(kw)
    desktop.get_state = lambda: (_ for _ in ()).throw(AssertionError('unexpected refresh'))
    inputs = compile_functions(source / 'tools/input.py',
                               ['_as_loc', '_resolve_label', 'click_tool'],
                               {'json': json, 'get_desktop': lambda: desktop})
    receipt = inputs['click_tool'](label=0)
    assert clicks == [{'loc': [100, 200], 'button': 'left', 'clicks': 1}]
    results.append({'id': 'P3', 'fact': 'Click(label=0) used stored coordinates without refreshing state',
                    'coordinates': clicks[0]['loc'], 'receipt': receipt,
                    'scope': 'Original Python label resolver and tool body; mouse dispatch stubbed'})

    sys.path[:0] = [str(root / 'src'), str(root / 'tests')]
    from test_cli import App, Element, FakeXa11y
    from bokkio.xa11y_backend import Xa11yBackend
    reads = []
    own = Element('window', 'Owned', children=[Element('button', 'Save')])
    unrelated = Element('window', 'Unrelated', children=[Element('button', 'Other')])
    original_children = unrelated.children
    unrelated.children = lambda: (reads.append('Unrelated'), original_children())[1]
    app = App(own)
    app.element.children_values = [unrelated, own]
    backend = Xa11yBackend(FakeXa11y(), platform='windows')
    backend._resolve_app = lambda _: app
    observed = backend.snapshot('100', 'Owned')
    assert reads == ['Unrelated'] and [n['name'] for n in observed['windows']] == ['Owned']
    results.append({'id': 'P4', 'fact': 'Bokkio Windows exact-window snapshot still traversed another window',
                    'unrelated_subtree_reads': len(reads), 'returned_windows': ['Owned'],
                    'scope': 'Real Xa11yBackend with repository fake element provider'})

    from bokkio.runtime import Runtime
    from bokkio.local_runtime import LocalRuntime
    class CountingBackend:
        def apps(self):
            return [{'pid': os.getpid(), 'name': 'ReviewFixture', 'is_foreground': True}]

        def snapshot(self, *args):
            self.constructed = 31
            nodes = [{'ref': 'n' + str(i), 'role': 'button', 'name': str(i),
                      'value': None, 'children': [], 'parent': 'root',
                      'state': {}, 'actions': [], 'bounds': None, 'platform_data': {}}
                     for i in range(30)]
            window = {'ref': 'root', 'role': 'window', 'name': 'Owned',
                      'children': nodes, 'parent': None}
            return {'app': {'pid': os.getpid(), 'name': 'ReviewFixture'}, 'windows': [window]}

    with tempfile.TemporaryDirectory(prefix='bokkio-review-') as folder:
        backend = CountingBackend()
        runtime = Runtime(Path(folder) / 'restricted', {'apps': ['ReviewFixture']},
                          backend=backend, birth_probe=lambda _: 'fixture-birth')
        local = LocalRuntime(Path(folder) / 'local', backend=backend, birth_probe=lambda _: 'fixture-birth')
        try:
            opened = runtime.call('session.open', {'apps': ['ReviewFixture']})
            assert opened['status'] == 'completed', opened
            observed = runtime.call('desktop.observe', {'app': 'ReviewFixture', 'max_nodes': 1},
                                    session_id=opened['session_id'])
            assert observed['status'] == 'completed', observed
            result = observed['result']
            assert len(result['nodes']) == 1 and result['total_nodes'] == backend.constructed == 31
            results.append({'id': 'P5', 'fact': 'max_nodes limits returned nodes after backend snapshot',
                            'backend_nodes': 31, 'returned_nodes': 1,
                            'scope': 'Real Runtime and SQLite with explicit fake snapshot provider'})
            assert runtime.policy['require_approval'] is True
            assert local.policy['require_approval'] is False
            results.append({'id': 'P6', 'fact': 'Restricted Runtime and LocalRuntime have different defaults',
                            'Runtime_require_approval': True, 'LocalRuntime_require_approval': False,
                            'LocalRuntime_trusted_host': local.policy['trusted_host']})
        finally:
            runtime._native_executor.shutdown(wait=True)
            local._native_executor.shutdown(wait=True)
    return {'scope': 'Six Python behavior probes, no Windows GUI integration',
            'passed': len(results), 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-source', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run(args.windows_source.resolve(), args.root.resolve())
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(content)
    print(content, end='')
