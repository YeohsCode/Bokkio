"""Benchmark evidence must come from the isolated native source and save flow."""
import importlib.util
import sys
from pathlib import Path
import pytest


sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('verify_waa_longchain', Path(__file__).parents[1] / 'scripts' / 'verify_waa_longchain.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.pop(0)


@pytest.mark.parametrize('variant', list(module.VARIANTS))
def test_variation_oracle_rejects_extra_content_and_never_creates_deliverable(tmp_path, variant):
    source = tmp_path / 'source'; source.mkdir()
    inputs, instruction, expected = module.prepare_variant(variant, source)
    artifact = tmp_path / 'result.txt'
    assert inputs and instruction and not artifact.exists()
    assert not module.evaluate_variant(module.VARIANTS[variant], artifact, expected)
    content = expected if isinstance(expected, str) else '\n'.join(expected)
    artifact.write_text(content)
    assert module.evaluate_variant(module.VARIANTS[variant], artifact, expected)
    artifact.write_text(content + '\nextra')
    assert not module.evaluate_variant(module.VARIANTS[variant], artifact, expected)
    if isinstance(expected, list):
        artifact.write_text(content + '\n' + expected[0])
        assert not module.evaluate_variant(module.VARIANTS[variant], artifact, expected)


def test_exact_limit_is_excluded_from_independent_size_oracle(tmp_path):
    inputs, _, expected = module.prepare_variant('size-boundary', tmp_path)
    sizes = {p.name:p.stat().st_size for p in inputs}
    assert sizes['exact limit.bin'] == 5*1024*1024
    assert expected == ['above limit.bin']


def test_pause_is_triggered_by_native_editor_write_not_dialog_path_write():
    class Backend:
        def perform(self, app, action, **kwargs):
            return {'before':{'role':kwargs['role']}}
    backend = module.PauseAfterEditorWrite(Backend())
    backend.perform('1', 'set_value', role='text_field')
    assert backend.writes == 0
    backend.perform('1', 'set_value', role='text_area')
    assert backend.writes == 1


def test_input_instruction_uses_isolated_paths_at_point_of_reference(tmp_path):
    source=tmp_path/'Documents'; source.mkdir()
    input_file=source/'largefile.txt'; output=source/'example_count.txt'
    goal=module.adapted_goal('Open "largefile.txt" from the Documents folder, count example, and save "example_count.txt".',
                            {'Documents':source}, [input_file], output)
    assert f'Open "{input_file}" from the folder "{source}"' in goal
    assert 'count example' in goal and 'save "example_count.txt"' in goal
    assert 'pinned personal folders are outside this task' in goal
    assert not input_file.exists() and not output.exists()


def test_changed_evaluator_is_rejected_before_import(tmp_path):
    (tmp_path / 'upstream_metrics.py').write_text('raise AssertionError("must not execute")')
    with pytest.raises(RuntimeError, match='export hash changed'):
        module.load_metrics(tmp_path)


def test_explorer_scope_cannot_be_changed_by_generated_window_selector():
    class Backend:
        def snapshot(self, app, window): return {'app':app,'window':window}
        def perform(self, app, action, **kwargs): return kwargs
    scoped = module.ScopedBackend(Backend(), {'pid':42,'hwnd':100})
    assert scoped.snapshot('42','another user window')['window'] == 'hwnd:0x64'
    assert scoped.perform('42','click',window='outside',expected_snapshot='digest')['window'] == 'hwnd:0x64'
    assert scoped.snapshot('43','Untitled')['window'] == 'Untitled'


def test_existing_file_without_native_source_and_save_evidence_is_not_completion(tmp_path):
    source=tmp_path/'Pictures';source.mkdir()
    input_file=source/'image.png';input_file.write_bytes(b'input')
    artifact=source/'png_files.txt';artifact.write_text('image.png')
    # Even if a model's text looks correct, it does not prove native source
    # observation, a Save As dialog, the save path, or a dispatched Save action.
    trace={'events':[{'kind':'planner_observations','observations':{'1':{'nodes':[
        {'role':'text_area','name':'Text Editor','value':'image.png'}]}}}]}
    checks=module.checks_from_trace(trace,source,artifact,'png-list',[input_file])
    assert checks['text_observed_natively']
    assert not checks['source_observed_natively']
    assert not checks['save_dialog_observed']
    assert not checks['save_target_observed']
    assert not checks['native_save_dispatched']


def test_word_count_needs_input_text_read_not_just_a_correct_numeric_output(tmp_path):
    source=tmp_path/'Documents';source.mkdir()
    (source/'largefile.txt').write_text('example example')
    artifact=source/'example_count.txt';artifact.write_text('2')
    trace={'events':[{'kind':'planner_observations','observations':{'1':{'nodes':[
        {'role':'text_area','name':'Text Editor','value':'2'}]}}}]}
    assert not module.checks_from_trace(trace,source,artifact,'word-count',[])['source_observed_natively']


def test_save_menu_invocation_is_not_a_save_dialog_button_dispatch(tmp_path):
    source = tmp_path / 'Pictures'; source.mkdir()
    trace = {'events': [{'kind': 'action', 'result': {'before': {'name': 'Save', 'role': 'menu_item'}, 'action': 'click'}}]}
    assert not module.checks_from_trace(trace, source, source / 'png_files.txt', 'png-list', [])['native_save_dispatched']
    trace['events'][0]['result']['before']['role'] = 'button'
    assert module.checks_from_trace(trace, source, source / 'png_files.txt', 'png-list', [])['native_save_dispatched']


def test_hidden_final_suffix_does_not_strip_a_second_suffix_from_source_evidence(tmp_path):
    p=tmp_path/'ignore.png.txt'; p.write_text('input')
    trace={'events':[{'kind':'planner_observations','observations':{'1':{'nodes':[
        {'role':'list_item','name':'ignore.png'}]}}}]}
    assert module.checks_from_trace(trace,tmp_path,tmp_path/'output.txt','png-list',[p])['source_observed_natively']
    assert not module.checks_from_trace(trace,tmp_path,tmp_path/'output.txt','png-list',[p],require_full_names=True)['source_observed_natively']
    trace['events'][0]['observations']['1']['nodes'][0]['name']=p.name
    assert module.checks_from_trace(trace,tmp_path,tmp_path/'output.txt','png-list',[p],require_full_names=True)['source_observed_natively']
