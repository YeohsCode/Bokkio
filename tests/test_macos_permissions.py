import sys
from pathlib import Path

from bokkio.macos_permissions import permission_message, permission_paths
from bokkio.model import BokkioPermissionError


def test_desktop_error_names_exact_app_and_executing_binary(monkeypatch):
    app='/Users/test/Applications/Bokkio.app'
    monkeypatch.setenv('BOKKIO_DESKTOP_APP_PATH',app)
    error=BokkioPermissionError.from_platform(RuntimeError('Accessibility Permission denied'))
    assert app in str(error) and str(Path(sys.executable).resolve()) in str(error)
    assert 'open -R' in str(error) and 'host application or' not in str(error)
    assert 'then restart' not in str(error)


def test_cli_error_shows_resolved_binary_without_inventing_host(monkeypatch):
    monkeypatch.delenv('BOKKIO_DESKTOP_APP_PATH',raising=False)
    value=permission_paths()
    assert value['authorization_path']==str(Path(sys.executable).resolve())
    assert value['application_path']=='' and 'Privacy_Accessibility' in permission_message()


def test_harness_preserves_app_identity_for_both_jev_modes():
    from bokkio.desktop_chat import mcp_environment_keys,patch_yaml
    for enabled in [True,False]:
        assert 'BOKKIO_DESKTOP_APP_PATH' in mcp_environment_keys(enabled)
        assert 'BOKKIO_DESKTOP_APP_PATH' in patch_yaml(['__BOKKIO_MCP_ENV__'],enabled)


def test_helper_commands_quote_literal_shell_metacharacters(monkeypatch):
    import shlex
    app='/Users/test/Apps $(ignored)/Bokkio.app'
    monkeypatch.setenv('BOKKIO_DESKTOP_APP_PATH',app)
    assert shlex.split(permission_paths()['commands'][0])==['open','-R',app]
