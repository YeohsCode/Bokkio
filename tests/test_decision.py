import json
from dataclasses import replace
from io import BytesIO
import pytest
from bokkio.decision import decide, execute_decision, options
from bokkio.jev import JevProvider
from bokkio.model import BokkioActionError, BokkioError
from test_cli import backend_with_button


class Provider:
    def __init__(self, choice=None, confidence=0.9, satisfied=0.0):
        self.choice, self.confidence, self.satisfied = choice, confidence, satisfied

    def ask(self, state, questions):
        self.state, self.questions = state, questions
        choice = self.choice or next(k for k in questions["next"]["criteria"] if k != "done")
        answers = {"next": {"type": "choice", "choice": choice, "confidence": self.confidence,
                           "probabilities": {k: float(k == choice) for k in questions["next"]["criteria"]}},
                   "goal_satisfied": {"type": "noul", "noul": self.satisfied}}
        for head, question in questions.items():
            if head.endswith("_target"):
                token = next(iter(question["criteria"]))
                answers[head] = {"type": "choice", "choice": token, "confidence": 0.95,
                                 "probabilities": {k: float(k == token) for k in question["criteria"]}}
        return {"model": "fake-offline", "answers": answers}



def test_valid_closed_choice_executes_against_same_observation():
    b, _, button = backend_with_button()
    decision, _ = decide(Provider(), "Click Save", b.snapshot("TextEdit"))
    assert decision.action == "click" and decision.value is None
    result = execute_decision(b, "TextEdit", decision)
    assert result["after"]["value"] == "pressed"


def test_unverified_native_outcome_does_not_offer_done_or_unrelated_expansion():
    from test_cli import Element
    b, window, _=backend_with_button()
    dropdown=Element('combo_box','File name:');dropdown.actions=['expand']
    window.children_values.append(dropdown)
    provider=Provider(choice='click')
    decision,_=decide(provider,'Click Save',b.snapshot('TextEdit'),allow_done=False)
    assert decision.action=='click'
    assert 'done' not in provider.questions['next']['criteria']
    assert 'expand' not in provider.questions['next']['criteria']
    assert provider.state['native_success_verified'] is False


def test_empty_name_narrowing_falls_back_to_same_scope_for_parent_menu():
    from test_cli import Element
    from bokkio.model import tree_digest
    backend,window,_=backend_with_button()
    name=Element('text_field','Name','file.png'); name.actions=['set_value']
    show=Element('menu_item','Show'); show.actions=['expand'];show.expanded=False
    window.children_values=[name,show]
    snapshot=backend.snapshot('TextEdit'); provider=Provider(choice='expand')
    decision,_=decide(provider,'Enable file name extensions',snapshot,allow_done=False)
    assert decision.action=='expand' and decision.snapshot_id==tree_digest(snapshot['windows'])
    assert any(row[3]=='Show' for row in provider.state['nodes'])
    assert 'done' not in provider.questions['next']['criteria']
    window.children_values=[name,Element('menu_item','Show'),Element('menu_item','Show')]
    for menu in window.children_values[1:]:menu.actions=['expand'];menu.expanded=False
    with pytest.raises(BokkioError,match='No native action candidates'):
        decide(provider,'Enable file name extensions',backend.snapshot('TextEdit'),allow_done=False)


def test_open_popup_keeps_show_submenu_when_view_toolbar_is_named():
    from test_cli import Element
    backend,window,_=backend_with_button()
    view=Element('button','View');view.actions=['press','expand'];view.expanded=True
    show=Element('menu_item','Show');show.actions=['expand'];show.expanded=False
    popup=Element('window','Popup',children=[show])
    window.children_values=[view,popup];view.parent_value=window;popup.parent_value=window
    provider=Provider(choice='expand')
    decision,_=decide(provider,'Enable file name extensions in the View menu',backend.snapshot('TextEdit'),allow_done=False)
    assert decision.action=='expand'
    assert any(c['name']=='Show' for c in provider.questions['expand_target']['criteria'].values())


@pytest.mark.parametrize("destination", [r'C:\Tasks\Desktop\report.txt', r'"C:\Task files\Desktop\report.txt"'])
def test_save_destination_and_dialog_name_do_not_expand_action_candidates(destination):
    from bokkio.decision import bounded_observation
    from bokkio.selector import flatten
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values = [Element('dialog', 'Save As', children=[
        Element('button', 'Save'), Element('button', 'Cancel'), Element('tree_item', 'Desktop'),
        Element('text_field', 'Name')])]
    snapshot = backend.snapshot('TextEdit')
    goal = f'Click the Save button in the Save As dialog to save at {destination}'
    goal += '\nRequired observable outcome: ' + json.dumps([{'role': 'window', 'name': 'report.txt - Notepad', 'field': 'name', 'equals': 'report.txt - Notepad'}])
    scoped = bounded_observation(goal, snapshot)
    nodes = {n['ref']: n for n in flatten(scoped['windows'])}
    assert {nodes[r]['name'] for r in scoped['observation_scope']['candidate_refs']} == {'Save'}
    assert any(n['name'] == 'Save As' for n in nodes.values())


def test_file_name_phrase_keeps_dialog_editor_and_excludes_file_row_name():
    from bokkio.decision import bounded_observation
    from bokkio.selector import flatten
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values = [Element('text_field','Name','existing.txt'), Element('text_field','File name:','')]
    scoped = bounded_observation('Enter the path in the File name field', backend.snapshot('TextEdit'))
    nodes = {n['ref']:n for n in flatten(scoped['windows'])}
    assert {nodes[r]['name'] for r in scoped['observation_scope']['matched_refs']} == {'File name:'}


def test_short_save_label_is_kept_when_mentioned_outside_save_as():
    from bokkio.decision import bounded_observation
    from bokkio.selector import flatten
    from test_cli import Element
    backend, window, _ = backend_with_button()
    window.children_values=[Element('button','Save'),Element('menu_item','Save As')]
    scoped=bounded_observation('Click Save after opening Save As', backend.snapshot('TextEdit'))
    nodes={n['ref']:n for n in flatten(scoped['windows'])}
    assert {nodes[r]['name'] for r in scoped['observation_scope']['matched_refs']} == {'Save','Save As'}


@pytest.mark.parametrize("confidence", [0.2, float("nan"), float("inf"), 1.1, True, "0.9"])
def test_low_or_invalid_confidence_never_executes(confidence):
    b, _, button = backend_with_button()
    with pytest.raises(BokkioError): decide(Provider(confidence=confidence), "Click Save", b.snapshot("TextEdit"))
    assert button.value is None


def test_invented_choice_rejected():
    b, _, button = backend_with_button()
    with pytest.raises(BokkioError, match="outside"):
        decide(Provider(choice="invented-ref"), "Click Save", b.snapshot("TextEdit"))
    assert button.value is None


def test_pending_or_contradictory_completion_rejected():
    b, _, _ = backend_with_button()
    with pytest.raises(BokkioError, match="unconfirmed"):
        decide(Provider(choice="done"), "Click Save", b.snapshot("TextEdit"))
    with pytest.raises(BokkioError, match="contradicts"):
        decide(Provider(satisfied=1), "Click Save", b.snapshot("TextEdit"))
    decision, _ = decide(Provider(choice="done", satisfied=1), "Goal met", b.snapshot("TextEdit"))
    assert execute_decision(b, "TextEdit", decision)["verification"] == "model_reported"


def test_state_change_and_ref_mismatch_block_before_dispatch():
    b, _, button = backend_with_button()
    snapshot = b.snapshot("TextEdit")
    decision, _ = decide(Provider(), "Click Save", snapshot)
    button.value = "new state"
    with pytest.raises(BokkioActionError, match="Snapshot changed"):
        execute_decision(b, "TextEdit", decision)
    assert button.value == "new state"
    button.value = None
    with pytest.raises(BokkioError, match="stale_ref"):
        execute_decision(b, "TextEdit", replace(decision, ref="missing"))
    with pytest.raises(BokkioActionError, match="not advertised"):
        execute_decision(b, "TextEdit", replace(decision, action="type", value="bad"))
    assert button.value is None


def test_text_is_selected_only_from_caller_values_and_empty_is_preserved():
    b, _, button = backend_with_button(); button.actions = ["set_value"]
    snapshot = b.snapshot("TextEdit")
    assert list(options(snapshot, ())) == ["done"]
    choices = options(snapshot, ("", "literal"))
    assert {c["value"] for c in choices.values() if c["action"] != "done"} == {"", "literal"}
    provider = Provider()
    decision, _ = decide(provider, "Clear field", snapshot, ("",))
    assert decision.value == ""
    assert execute_decision(b, "TextEdit", decision)["verification"] == "confirmed"
    assert all("platform_data" not in n for n in provider.state["nodes"])


def test_transport_encodes_official_wire_format_and_reports_usage():
    seen = {}
    def open_request(request, timeout):
        seen.update(payload=json.loads(request.data), auth=request.get_header("Authorization"), timeout=timeout)
        return BytesIO(json.dumps({"model": "jev-latest", "answers": {}, "usage": {"input_tokens": 10, "output_tokens": 2}}).encode())
    client = JevProvider(api_key="offline-test-secret", opener=open_request)
    result = client.ask({"goal": "test"}, {"next": {"type": "choice", "criteria": {"done": "done"}}})
    assert seen["auth"] == "Bearer offline-test-secret"
    assert seen["payload"]["model"] == "jev-latest"
    assert result["usage"]["input_tokens"] == 10 and result["elapsed_seconds"] >= 0
    assert "offline-test-secret" not in json.dumps(result)


def test_malformed_response_and_missing_credentials_are_explicit(monkeypatch):
    b, _, _ = backend_with_button()
    class Malformed:
        def ask(self, *_): return {"answers": {}}
    with pytest.raises(BokkioError, match="Malformed"):
        decide(Malformed(), "click", b.snapshot("TextEdit"))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("BOKKIO_JEV_CONFIG", "/tmp/bokkio-missing-test-config.json")
    with pytest.raises(BokkioError, match="not configured"): JevProvider()


def test_indistinguishable_duplicate_refs_are_excluded_from_decisions():
    from test_cli import Element
    b, window, button = backend_with_button()
    window.children_values.append(Element("button", "Save"))
    snapshot = b.snapshot("TextEdit")
    assert list(options(snapshot, ())) == ["done"]
    from bokkio.decision import Decision
    from bokkio.model import tree_digest
    ref = b.find("TextEdit", "button", "Save")[0]["ref"]
    guessed = Decision("click", ref, None, 0.9, tree_digest(snapshot["windows"]))
    with pytest.raises(BokkioActionError, match="indistinguishable"):
        execute_decision(b, "TextEdit", guessed)
    assert button.value is None


def test_http_error_does_not_leak_credentials_or_response_body():
    import urllib.error
    def fail(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "secret response", {}, BytesIO(b'offline-test-secret'))
    provider = JevProvider(api_key="offline-test-secret", opener=fail)
    with pytest.raises(BokkioError) as error: provider.ask({}, {})
    assert str(error.value) == "Jev HTTP request failed with status 401"


def test_openrouter_private_config_and_environment_override(tmp_path, monkeypatch):
    path = tmp_path / "jev.json"
    path.write_text(json.dumps({"source": "openrouter", "api_key": "sk-or-offline", "model": "typesafe/jev-1.13"}))
    monkeypatch.setenv("BOKKIO_JEV_CONFIG", str(path))
    for key in ("OPENROUTER_API_KEY", "TYPESAFE_API_KEY", "BOKKIO_JEV_SOURCE", "BOKKIO_JEV_MODEL"):
        monkeypatch.delenv(key, raising=False)
    client = JevProvider()
    assert client.source == "openrouter" and client.endpoint == "https://openrouter.ai/api/alpha/decisions"
    assert client.model == "typesafe/jev-1.13"
    monkeypatch.setenv("TYPESAFE_API_KEY", "direct-offline")
    direct = JevProvider()
    assert direct.source == "typesafe" and direct.model == "jev-latest"
    with pytest.raises(BokkioError, match="OpenRouter keys require"):
        JevProvider(api_key="sk-or-offline", source="typesafe")


def test_noul_without_confidence_and_true_false_criteria():
    b, _, _ = backend_with_button(); provider = Provider()
    decision, _ = decide(provider, "Click Save", b.snapshot("TextEdit"))
    assert decision.action == "click"
    assert set(provider.questions["goal_satisfied"]["criteria"]) == {"true", "false"}


def test_only_selected_operation_target_head_is_consumed():
    b, _, button = backend_with_button(); button.actions.append("focus")
    class Poison(Provider):
        def ask(self, *args):
            response = super().ask(*args)
            response["answers"]["focus_target"] = {"choice": "invented", "confidence": float("nan")}
            return response
    decision, _ = decide(Poison(), "Click Save", b.snapshot("TextEdit"))
    assert execute_decision(b, "TextEdit", decision)["after"]["value"] == "pressed"


def test_selected_target_invalid_probability_prevents_execution():
    b, _, button = backend_with_button()
    class Wrong(Provider):
        def ask(self, *args):
            response = super().ask(*args)
            response["answers"]["click_target"]["probabilities"] = {"invented": 1.0}
            return response
    with pytest.raises(BokkioError, match="distribution"):
        decide(Wrong(), "Click Save", b.snapshot("TextEdit"))
    assert button.value is None


def test_window_scoped_decision_ignores_changes_in_other_window():
    from test_cli import Element
    b, _, button = backend_with_button()
    other = Element("window", "Other", children=[Element("button", "Other button")])
    app = b._resolve_app("TextEdit"); app.element.children_values.append(other)
    decision, _ = decide(Provider(), "Click Save", b.snapshot("TextEdit", "Untitled"))
    other.children_values[0].name = "Changed elsewhere"
    assert execute_decision(b, "TextEdit", decision)["after"]["value"] == "pressed"


def test_dense_window_uses_bounded_groups_and_observed_target():
    from test_cli import Element
    b, window, _ = backend_with_button()
    window.children_values = [Element("button", f"Control {i}") for i in range(300)]
    class Grouped(Provider):
        calls = 0
        def ask(self, state, questions):
            self.calls += 1
            for q in questions.values():
                assert len(q.get("criteria", {})) <= 255
            response = super().ask(state, questions)
            if "click_group" in questions:
                group = "g1"
                response["answers"]["click_group"] = {"type": "choice", "choice": group, "confidence": 0.95,
                    "probabilities": {k: float(k == group) for k in questions["click_group"]["criteria"]}}
            return response
    provider = Grouped()
    decision, response = decide(provider, "Click Control 240", b.snapshot("TextEdit"), narrow=False)
    assert provider.calls == 2
    assert b.get(decision.ref, "TextEdit")["name"] == "Control 240"
    assert len(response["calls"]) == 2


def test_thousand_targets_share_structure_and_defer_unselected_heads():
    from test_cli import Element
    b, window, _ = backend_with_button()
    window.children_values = [Element("button", f"Control {i}") for i in range(1000)]
    class Dense:
        calls = []
        def ask(self, state, questions):
            self.calls.append((state, questions))
            answers = {}
            for head, question in questions.items():
                if question["type"] == "noul":
                    answers[head] = {"type": "noul", "noul": 0}
                    continue
                criteria = question["criteria"]
                assert len(criteria) <= 255
                token = "click" if "click" in criteria else "g4" if "g4" in criteria else next(iter(criteria))
                answers[head] = {"type": "choice", "choice": token, "confidence": 0.95,
                                 "probabilities": {k: float(k == token) for k in criteria}}
            return {"answers": answers, "usage": {"input_tokens": 10}, "elapsed_seconds": 1}
    provider = Dense()
    decision, response = decide(provider, "Click Control 960", b.snapshot("TextEdit"), narrow=False)
    assert b.get(decision.ref, "TextEdit")["name"] == "Control 960"
    assert len(provider.calls) == 3
    assert set(provider.calls[0][1]) == {"next", "goal_satisfied"}
    assert set(provider.calls[1][1]) == {"click_group"}
    shared = provider.calls[0][0]
    assert "nodes" not in shared
    assert sum(len(g["members"]) for g in shared["groups"]) >= 1000
    assert response["usage"]["input_tokens"] == 30 and response["elapsed_seconds"] == 3


@pytest.mark.parametrize("goal", ["Click Sample 500", "点击Sample 500"])
def test_bounded_names_distinguish_numeric_suffix_and_keep_full_guard(goal):
    from test_cli import Element
    from bokkio.decision import bounded_observation
    b, window, _ = backend_with_button()
    window.children_values = [Element("button", f"Sample {i}") for i in range(1000)]
    snapshot = b.snapshot("TextEdit")
    scoped = bounded_observation(goal, snapshot)
    assert [n["name"] for n in scoped["windows"][0]["children"][0]["children"]] == ["Sample 500"]
    decision, _ = decide(Provider(choice="click"), "Click Sample 500", snapshot)
    assert b.get(decision.ref, "TextEdit")["name"] == "Sample 500"
    window.children_values[10].value = "changed outside model context"
    with pytest.raises(BokkioActionError, match="Snapshot changed"):
        execute_decision(b, "TextEdit", decision)


def test_bounded_context_keeps_duplicates_and_falls_back_without_names():
    from test_cli import Element
    from bokkio.decision import bounded_observation
    from bokkio.selector import flatten
    b, window, _ = backend_with_button()
    window.children_values = [Element("button", f"Sample {i}") for i in range(300)] + [Element("button", "Action"), Element("button", "Action")]
    snapshot = b.snapshot("TextEdit")
    scoped = bounded_observation("Click Action", snapshot)
    assert len([n for n in flatten(scoped["windows"]) if n["name"] == "Action"]) == 2
    assert bounded_observation("Find the best choice", snapshot) is snapshot
    assert list(options(scoped, [])) == ["done"]


def test_explicit_scroll_and_collapse_keep_context_actions():
    from test_cli import Element
    b, window, _ = backend_with_button()
    window.children_values = [Element("button", f"Sample {i}") for i in range(100)]
    snapshot = b.snapshot("TextEdit")
    container = snapshot["windows"][0]["children"][0]
    container["actions"] = ["scroll", "collapse"]
    container["state"]["expanded"] = True
    container["platform_data"]["scroll"] = {"x": {"scrollable": False, "position": 0, "view_size": 1},
                                           "y": {"scrollable": True, "position": 0, "view_size": 0.1}}
    provider = Provider(choice="click")
    decide(provider, "Click Sample 50", snapshot)
    assert "scroll_target" not in provider.questions and "collapse_target" not in provider.questions
    for action, goal in [("scroll", "Scroll down toward Sample 50"), ("collapse", "Collapse the container around Sample 50")]:
        decision, _ = decide(Provider(choice=action), goal, snapshot)
        assert decision.action == action and decision.ref == container["ref"]


def test_named_scroll_container_is_context_for_an_observed_click_target():
    from test_cli import Element
    b, window, _ = backend_with_button()
    group = Element("group", "Scale content", children=[Element("button", f"Sample {i}") for i in range(1000)])
    window.children_values = [group]; group.parent_value = window
    snapshot = b.snapshot("TextEdit")
    container = snapshot["windows"][0]["children"][0]["children"][0]
    container["actions"] = ["scroll"]
    container["platform_data"]["scroll"] = {"x": {"scrollable": False, "position": 0, "view_size": 1},
                                           "y": {"scrollable": True, "position": 0, "view_size": 0.1}}
    provider = Provider(choice="click")
    decision, _ = decide(provider, "Click Sample 619 in Scale content", snapshot)
    assert decision.action == "click" and "scroll_target" not in provider.questions
    scroll, _ = decide(Provider(choice="scroll"), "Scroll Scale content toward Sample 619", snapshot)
    assert scroll.action == "scroll" and scroll.ref == container["ref"]


@pytest.mark.parametrize('name,dialog_name',[('Open','Open'),('Save','Save As')])
def test_classic_confirmation_button_excludes_same_named_combo_arrows(name,dialog_name):
    from test_cli import Element
    from bokkio.selector import flatten
    backend,window,_=backend_with_button()
    controls=[]
    for label in ['File name:','Files of type:','Encoding:']:
        controls.append(Element('combo_box',label,children=[Element('button',name)]))
    confirm=Element('button',name);controls.append(confirm)
    dialog=Element('dialog',dialog_name,children=controls);window.children_values=[dialog]
    snapshot=backend.snapshot('TextEdit')
    for node in flatten(snapshot['windows']):
        node['platform']='windows'
        if node['role']=='dialog':node['platform_data']['class_name']='#32770'
    provider=Provider(choice='click')
    decision,_=decide(provider,f'Invoke the {name} button in the {dialog_name} dialog',snapshot,allow_done=False)
    candidates=provider.questions['click_target']['criteria']
    assert len(candidates)==1 and next(iter(candidates.values()))['parent_name']==dialog_name
    assert next(n for n in flatten(snapshot['windows']) if n['ref']==decision.ref)['parent']==next(n['ref'] for n in flatten(snapshot['windows']) if n['role']=='dialog')
