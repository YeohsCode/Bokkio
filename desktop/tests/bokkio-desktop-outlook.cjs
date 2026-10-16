// Real packaged UI + real PowerShell + owned offline Graph cmdlet fixture.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {_electron:electron}=require('playwright-core');
const root=path.resolve(__dirname,'../..'),output=process.env.BOKKIO_TEST_OUTPUT,pwsh=process.env.BOKKIO_TEST_PWSH;
if(!output||!pwsh)throw Error('Set isolated BOKKIO_TEST_OUTPUT and real BOKKIO_TEST_PWSH');
let app;const report={checks:[],scope:'packaged UI and shipped PowerShell script; owned offline Graph cmdlet fixture; no real account or token'};
function check(name,ok){assert(ok,name);report.checks.push({name,passed:true});console.log(name)}
async function launch(challenge=false){
 const inherited=Object.fromEntries(Object.entries(process.env).filter(([key])=>!['PATH','PSMODULEPATH'].includes(key.toUpperCase())));
 app=await electron.launch({executablePath:process.env.BOKKIO_ELECTRON,args:[path.join(root,'desktop')],env:{...inherited,PATH:path.dirname(pwsh)+path.delimiter+process.env.PATH,PSModulePath:path.join(output,'modules')+path.delimiter+(process.env.PSModulePath||''),BOKKIO_PWSH_FIXTURE_MODE:challenge?'challenge':'',BOKKIO_DESKTOP_STATE:path.join(output,'runtime'),BOKKIO_DESKTOP_USER_DATA:path.join(output,'host'),BOKKIO_PLANNER_CONFIG:path.join(output,'absent.json')},timeout:60000});
 const page=await app.firstWindow();page.setDefaultTimeout(30000);await page.getByRole('button',{name:'配置',exact:true}).click();return page;
}
const status=page=>page.getByRole('status',{name:'Outlook 连接状态',exact:true});
(async()=>{
 fs.mkdirSync(output,{recursive:true});const fixture=path.join(output,'modules/Microsoft.Graph.Authentication/99.0.0');fs.mkdirSync(fixture,{recursive:true});
 let module=fs.readFileSync(path.join(root,'tests/test_outlook_powershell.py'),'utf8').split("MODULE=r'''")[1].split("'''")[0];
 module=module.replace(" -or $decoded -notmatch 'receivedDateTime ge 2026-10-11T16:00:00Z' -or $decoded -notmatch 'receivedDateTime lt 2026-10-16T04:00:00Z'",'');
 fs.writeFileSync(path.join(fixture,'Microsoft.Graph.Authentication.psm1'),module);
 fs.writeFileSync(path.join(fixture,'Microsoft.Graph.Authentication.psd1'),"@{RootModule='Microsoft.Graph.Authentication.psm1';ModuleVersion='99.0.0';GUID='879297cc-155b-4cba-a395-a12a576fd100';FunctionsToExport='*'}");
 let page=await launch();check('packaged_application',await app.evaluate(({app})=>app.isPackaged));await status(page).filter({hasText:'未连接'}).waitFor();
 check('no_microsoft_password_field',await page.getByLabel('微软密码',{exact:true}).count()===0);
 await page.getByRole('button',{name:'连接 Outlook',exact:true}).click();await status(page).filter({hasText:'已连接'}).waitFor();check('connect_from_visible_settings',true);
 await page.getByRole('button',{name:'统计本周未读邮件',exact:true}).click();await page.locator('.outlook-settings .notice').filter({hasText:'3'}).waitFor();check('ui_query_executes_real_ps1_and_counts_pages',true);
 await page.locator('.outlook-settings').screenshot({path:path.join(output,'outlook-connected.png')});
 await app.close();app=null;page=await launch();await status(page).filter({hasText:'已连接'}).waitFor();check('connection_identity_rechecked_after_app_restart',true);
 const profile=JSON.parse(fs.readFileSync(path.join(output,'runtime/outlook-connection.json')));check('profile_contains_only_public_account_fields',Object.keys(profile).sort().join(',')==='account,scopes,tenant');
 await page.getByRole('button',{name:'退出 Graph 登录',exact:true}).click();await status(page).filter({hasText:'未连接'}).waitFor();check('logout_removes_bokkio_profile',!fs.existsSync(path.join(output,'runtime/outlook-connection.json')));
 await app.close();app=null;page=await launch(true);await status(page).filter({hasText:'未连接'}).waitFor();
 await page.getByRole('button',{name:'连接 Outlook',exact:true}).click();await status(page).filter({hasText:'等待微软确认'}).waitFor();check('device_challenge_visible',(await page.getByLabel('微软设备码').textContent())==='OWNEDTEST');
 await page.getByRole('button',{name:'取消连接',exact:true}).click();await status(page).filter({hasText:'已取消'}).waitFor();check('login_cancel_stops_waiting_process',true);
 await page.getByRole('button',{name:'录制',exact:true}).click();check('cancelled_login_does_not_block_navigation',await page.getByRole('button',{name:'开始录制',exact:true}).isVisible());
})().catch(async error=>{report.error=error.stack;process.exitCode=1;console.error(error.message);if(app){const page=app.windows()[0];report.visible_outlook_state=await page.locator('.outlook-settings').innerText().catch(()=> 'window closed');await page.screenshot({path:path.join(output,'outlook-failure.png')}).catch(()=>{});}}).finally(async()=>{if(app)await app.close();fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));});
