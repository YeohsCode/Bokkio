"""Send a real global recording shortcut while anchored to the owned editor."""
import sys
from pathlib import Path
from bokkio.app_launch import installed_running_apps
from bokkio.local_runtime import LocalRuntime
from bokkio.sdk import Client
from bokkio.runtime_workflow import runtime_snapshot

app_name, key, output = sys.argv[1:]
assert key in {'R','P','F12'}
apps=[a for a in installed_running_apps() if a['name'].casefold()==app_name.casefold()]
assert len(apps)==1
client=Client(LocalRuntime(Path(output)));client.open()
try:
    pid=apps[0]['pid'];windows=client.call('desktop.windows',{'app':str(pid)})['result']
    windows=[w for w in windows if w['role']=='window' and not w.get('minimized')]
    assert len(windows)==1
    window=windows[0]['name'];observed,snapshot=runtime_snapshot(client,pid,window)
    target=next(n for n in snapshot['windows'] if n['role']=='window' and n['name']==window)
    combo=('Command' if sys.platform=='darwin' else 'Ctrl')+'+Shift+'+key
    result=client.call('desktop.input',{'app':str(pid),'window':window,'observation_id':observed['result']['observation_id'],'ref':target['ref'],'action':'key','key':combo})
    assert result['status'] in {'executed','verified'},result
finally:client.call('session.close')
