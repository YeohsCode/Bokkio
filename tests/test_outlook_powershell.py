"""Run the shipped generic Graph bridge through real PowerShell with offline data."""
import os
from pathlib import Path
import shutil

import pytest
from bokkio.outlook_graph import GraphPowerShell, GraphError

PWSH=os.environ.get('BOKKIO_TEST_PWSH') or shutil.which('pwsh')
pytestmark=pytest.mark.skipif(not PWSH,reason='Requires real PowerShell 7')

MODULE=r'''
function Connect-MgGraph {
 param($Scopes,$ContextScope,[switch]$UseDeviceAuthentication,[switch]$NoWelcome)
 if ($ContextScope -ne 'CurrentUser' -or $Scopes -ne 'Mail.Read') { throw 'Unexpected auth contract' }
 if ($env:BOKKIO_PWSH_FIXTURE_MODE -match 'challenge') {
  $message='To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code OWNEDTEST to authenticate.'
  if ($env:BOKKIO_PWSH_FIXTURE_MODE -eq 'console_challenge') { [Console]::Write($message.Replace('https://microsoft.com/devicelogin','https://login.microsoft.com/device')) } else { Write-Warning $message }
  [Threading.Thread]::Sleep(30000)
 }
}
function Get-MgContext { [pscustomobject]@{Account='fixture@example.invalid';TenantId='fixture';Scopes=@('Mail.Read')} }
function Disconnect-MgGraph {}
function Invoke-MgGraphRequest {
 param($Method,$Uri,$OutputType,$Headers)
 if ($Method -ne 'GET') { throw 'Unexpected mutation' }
 @{method=$Method;uri=$Uri;headers=$Headers} | ConvertTo-Json -Compress | Add-Content (Join-Path $PSScriptRoot 'requests.jsonl')
 if ($Uri -match '/mailFolders/inbox\?') { return [pscustomobject]@{id='inbox'} }
 if ($Headers.Prefer -ne 'outlook.body-content-type="text"') { throw 'Missing body format preference' }
 if ($env:BOKKIO_PWSH_FIXTURE_MODE -eq 'failure') {
  $record=[Management.Automation.ErrorRecord]::new([Exception]::new('Graph request failed'),'BadRequest',[Management.Automation.ErrorCategory]::InvalidArgument,$null)
  $record.ErrorDetails=[Management.Automation.ErrorDetails]::new('{"error":{"code":"InefficientFilter","message":"Order the filtered properties before other properties."}}')
  throw $record
 }
 if ($env:BOKKIO_PWSH_FIXTURE_MODE -eq 'empty') { return [pscustomobject]@{value=@()} }
 if ($env:BOKKIO_PWSH_FIXTURE_MODE -eq 'external_next') { return [pscustomobject]@{value=@();'@odata.nextLink'='https://attacker.invalid/v1.0/me'} }
 if ($env:BOKKIO_PWSH_FIXTURE_MODE -eq 'large') { return [pscustomobject]@{id='large';body=[pscustomobject]@{content=('x'*600000)}} }
 if (([Uri]$Uri).AbsolutePath -eq '/v1.0/me/mailFolders') { return [pscustomobject]@{value=@([pscustomobject]@{id='inbox';displayName='Inbox'},[pscustomobject]@{id='sentitems';displayName='Sent Items'})} }
 $now=[DateTimeOffset]::UtcNow
 $rows=@(
  [pscustomobject]@{id='owned-release';subject='Release handoff';isRead=$false;receivedDateTime=$now.AddHours(-2).ToString('o');from=@{emailAddress=@{address='release@example.invalid'}};body=@{contentType='text';content='发布交接：回滚窗口为今晚22:00，负责人是林舟。'}},
  [pscustomobject]@{id='owned-budget';subject='Budget review';isRead=$true;receivedDateTime=$now.AddHours(-6).ToString('o');from=@{emailAddress=@{address='finance@example.invalid'}};body=@{contentType='text';content='预算复核：批准测试额度730元，周五提交结果。'}},
  [pscustomobject]@{id='owned-older';subject='Earlier note';isRead=$false;receivedDateTime=$now.AddHours(-20).ToString('o');from=@{emailAddress=@{address='release@example.invalid'}};body=@{contentType='text';content='昨天的旧记录，不属于最近12小时。'}},
  [pscustomobject]@{id='owned-oldest';subject='Old archive';isRead=$false;receivedDateTime=$now.AddHours(-48).ToString('o');from=@{emailAddress=@{address='other@example.invalid'}};body=@{contentType='text';content='两天以前的归档。'}}
 )
 $parsed=[Uri]$Uri
 if ($parsed.AbsolutePath -match '/me/messages/([^/]+)$') { return ($rows | Where-Object id -eq $Matches[1]) }
 $query=@{}
 foreach ($pair in $parsed.Query.TrimStart('?').Split('&')) {
  if (!$pair) { continue }; $parts=$pair.Split('=',2)
  $query[[Uri]::UnescapeDataString($parts[0])]=[Uri]::UnescapeDataString($parts[1].Replace('+',' '))
 }
 $filter=$query['$filter']
 if ($filter -match 'receivedDateTime ge ([0-9T:.+Z-]+)') { $start=[DateTimeOffset]::Parse($Matches[1]);$rows=@($rows | Where-Object { [DateTimeOffset]::Parse($_.receivedDateTime) -ge $start }) }
 if ($filter -match 'receivedDateTime lt ([0-9T:.+Z-]+)') { $end=[DateTimeOffset]::Parse($Matches[1]);$rows=@($rows | Where-Object { [DateTimeOffset]::Parse($_.receivedDateTime) -lt $end }) }
 if ($filter -match 'isRead eq false') { $rows=@($rows | Where-Object { !$_.isRead }) }
 if ($filter -match "from/emailAddress/address eq '([^']+)'") { $sender=$Matches[1];$rows=@($rows | Where-Object { $_.from.emailAddress.address -eq $sender }) }
 $total=$rows.Count
 $top=if ($query['$top']) { [int]$query['$top'] } else { 10 }
 $top=[Math]::Min(1,$top)
 $offset=if ($query['fixture_offset']) { [int]$query['fixture_offset'] } else { 0 }
 $values=@($rows | Select-Object -Skip $offset -First $top)
 if ($query['$select']) { $values=@($values | Select-Object -Property $query['$select'].Split(',')) }
 $result=[pscustomobject]@{value=$values}
 if ($query['$count'] -eq 'true') { $result | Add-Member -NotePropertyName '@odata.count' -NotePropertyValue $total }
 if ($offset+$values.Count -lt $total) {
  $base=($Uri -replace '&?fixture_offset=\d+','' -replace '&?\$skiptoken=owned%2B%3D','')
  $next=$base+$(if ($base.Contains('?')) {'&'} else {'?'})+'fixture_offset='+($offset+$top)+'&$skiptoken=owned%2B%3D'
  $result | Add-Member -NotePropertyName '@odata.nextLink' -NotePropertyValue $next
 }
 return $result
}
Export-ModuleMember -Function *
'''


@pytest.fixture
def graph(tmp_path,monkeypatch):
    folder=tmp_path/'modules/Microsoft.Graph.Authentication/99.0.0';folder.mkdir(parents=True)
    (folder/'Microsoft.Graph.Authentication.psm1').write_text(MODULE)
    (folder/'Microsoft.Graph.Authentication.psd1').write_text("@{RootModule='Microsoft.Graph.Authentication.psm1';ModuleVersion='99.0.0';GUID='879297cc-155b-4cba-a395-a12a576fd100';FunctionsToExport='*'}")
    monkeypatch.setenv('PSModulePath',str(tmp_path/'modules')+os.pathsep+os.environ.get('PSModulePath',''))
    monkeypatch.setattr(GraphPowerShell,'executable',lambda _:PWSH)
    return GraphPowerShell(tmp_path/'runtime')


def test_real_ps1_generic_filters_body_pagination_and_logout(graph,monkeypatch):
    from datetime import datetime,timedelta,timezone
    assert graph.run('connect')['status']=='connected'
    now=datetime.now(timezone.utc)
    query={'$filter':f"receivedDateTime ge {(now-timedelta(hours=12)).isoformat()} and receivedDateTime lt {now.isoformat()}",'$select':'id,subject,body','$top':'1'}
    result=graph.request('/me/messages',query)
    assert not result['complete'] and result['pages']==1 and len(result['data']['value'])==1
    assert '22:00' in result['data']['value'][0]['body']['content']
    assert '%2B%3D' in result['next_link']
    next_page=graph.request(result['next_link'])
    assert next_page['complete'] and '730' in next_page['data']['value'][0]['body']['content']
    all_pages=graph.request('/me/messages',query,max_pages=2)
    assert all_pages['complete'] and len(all_pages['data']['value'])==2
    unread=graph.request('/me/mailFolders/inbox/messages',{'$filter':'isRead eq false','$select':'id','$count':'true'},max_pages=4)
    assert unread['data']['@odata.count']==3
    assert all('body' not in item for item in unread['data']['value'])
    assert len(graph.request('/me/mailFolders')['data']['value'])==2
    assert graph.request('/me/messages/owned-budget')['data']['body']['content'].startswith('预算')
    monkeypatch.setenv('BOKKIO_PWSH_FIXTURE_MODE','empty')
    assert graph.request('/me/messages')['data']['value']==[]
    assert graph.run('disconnect')['status']=='disconnected' and not graph.profile.exists()


@pytest.mark.parametrize('mode,code',[('external_next','invalid_request'),('large','response_too_large'),('failure','InefficientFilter')])
def test_real_ps1_errors_do_not_return_partial_success(graph,monkeypatch,mode,code):
    assert graph.run('connect')['status']=='connected'
    monkeypatch.setenv('BOKKIO_PWSH_FIXTURE_MODE',mode)
    with pytest.raises(GraphError) as error:graph.request('/me/messages')
    assert error.value.code==code


@pytest.mark.parametrize('mode',['challenge','console_challenge'])
def test_real_ps1_auth_challenge_is_streamed_without_waiting_for_login(graph,monkeypatch,mode):
    monkeypatch.setenv('BOKKIO_PWSH_FIXTURE_MODE',mode)
    assert graph.run('check')['status']=='needs_login'
