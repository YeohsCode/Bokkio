$ErrorActionPreference='Stop'
$root='C:\BokkioWorkspace\office-install'
function Report($data) { $data | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 "$root\status.json" }
try {
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 $admin=[Security.Principal.WindowsPrincipal]::new($identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
 if(-not $admin){throw 'Installer requires elevation'}
 $signature=Get-AuthenticodeSignature "$root\setup.exe"
 if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation'){throw 'Invalid installer signature'}
 Report @{stage='installing';started=(Get-Date -Format o);administrator=$admin;product='O365ProPlusRetail';architecture='64';language='en-us'}
 $process=Start-Process "$root\setup.exe" -ArgumentList '/configure',"$root\configuration.xml" -PassThru -Wait
 $apps=@('WINWORD','EXCEL','POWERPNT','OUTLOOK','ONENOTE','MSACCESS','MSPUB') | ForEach-Object {
   $path="C:\Program Files\Microsoft Office\root\Office16\$_.EXE"
   @{name=$_;path=$path;installed=(Test-Path $path);version=$(if(Test-Path $path){(Get-Item $path).VersionInfo.FileVersion}else{$null})}
 }
 $config=Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Office\ClickToRun\Configuration' -ErrorAction SilentlyContinue
 Report @{stage='finished';exit_code=$process.ExitCode;apps=@($apps);configuration=@{version=$config.VersionToReport;platform=$config.Platform;products=$config.ProductReleaseIds};finished=(Get-Date -Format o)}
} catch { Report @{stage='failed';error=$_.Exception.Message} }
Set-Content "$root\install.done" 'done'
