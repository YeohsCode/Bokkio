import pytest
from test_cli import App,Element,FakeXa11y
from bokkio.xa11y_backend import Xa11yBackend


def backend(windows):
    app=App(windows[0]);app.element.children_values=windows
    result=Xa11yBackend(FakeXa11y(),platform='macos');result._resolve_app=lambda _:app
    return result


def test_exact_window_scope_preserves_refs_and_avoids_unrelated_document_reads():
    own=Element('window','Owned',children=[Element('button','Save')])
    unrelated=Element('window','Unrelated',children=[Element('button','Delete')])
    b=backend([unrelated,own]);full=b.snapshot('TextEdit')
    original=full['windows'][0]['children'][1]['children'][0]['ref']
    unrelated.children=lambda:pytest.fail('unrelated document body must not be read')
    scoped=b.snapshot('TextEdit','Owned')
    assert scoped['windows'][0]['children'][0]['ref']==original
    response=b.perform('TextEdit','click',ref=original,window='Owned')
    assert own.children_values[0].value=='pressed'


def test_same_title_windows_still_have_distinct_refs_and_are_not_dropped():
    b=backend([Element('window','Same'),Element('window','Same')])
    nodes=b.snapshot('TextEdit','Same')['windows']
    assert len(nodes)==2 and len({n['ref'] for n in nodes})==2


def test_legacy_substring_window_selection_is_preserved():
    b=backend([Element('window','Owned document'),Element('window','Other')])
    assert b.snapshot('TextEdit','document')['windows'][0]['name']=='Owned document'
