// Packaged UI + real PowerShell. Mail is owned offline data; optional real model.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {_electron:electron}=require('playwright-core');
const root=path.resolve(__dirname,'../..'),output=process.env.BOKKIO_TEST_OUTPUT,pwsh=process.env.BOKKIO_TEST_PWSH;
if(!output||!pwsh)throw Error('Set isolated BOKKIO_TEST_OUTPUT and real BOKKIO_TEST_PWSH');
let app;const report={checks:[],scope:'packaged UI and shipped PowerShell; owned offline Graph data, no real Microsoft account or token',model_chat:'not requested'};
function check(name,ok){assert(ok,name);report.checks.push({name,passed:true});console.log(name)}
async function launch(challenge=false){
 const inherited=Object.fromEntries(Object.entries(process.env).filter(([key])=>!['PATH','PSMODULEPATH'].includes(key.toUpperCase())));
 app=await electron.launch({executablePath:process.env.BOKKIO_ELECTRON,args:[path.join(root,'desktop')],env:{...inherited,PATH:path.dirname(pwsh)+path.delimiter+process.env.PATH,PSModulePath:path.join(output,'modules')+path.delimiter+(process.env.PSModulePath||''),BOKKIO_PWSH_FIXTURE_MODE:challenge?'challenge':'',BOKKIO_DESKTOP_STATE:path.join(output,'runtime'),BOKKIO_DESKTOP_USER_DATA:path.join(output,'host'),BOKKIO_PLANNER_CONFIG:path.join(output,'absent.json')},timeout:60000});
 const page=await app.firstWindow();page.setDefaultTimeout(30000);await page.getByRole('button',{name:'配置',exact:true}).click();return page;
}
const status=page=>page.getByRole('status',{name:'Outlook 连接状态',exact:true});
async function chat(page,prompt,name,expected){
 await page.getByRole('button',{name:'对话',exact:true}).click();
 await page.locator('.composer textarea').fill(prompt);await page.getByRole('button',{name:'执行任务',exact:true}).click();
 await page.locator('.message.user').filter({hasText:prompt}).waitFor();
 await page.locator('.task-card > .pill').filter({hasText:/已完成|失败|已取消/}).waitFor({timeout:300000});
 const state=await page.locator('.task-card > .pill').textContent();
 if(state!=='已完成')throw Error(name+' task '+state+': '+await page.locator('.conversation').innerText());
 const answer=await page.locator('.message.assistant').last().textContent();
 fs.writeFileSync(path.join(output,name+'-answer.txt'),answer);
 check(name+'_answer_matches_owned_mail',expected(answer));
 await page.locator('.conversation').screenshot({path:path.join(output,name+'.png')});
}
(async()=>{
 fs.mkdirSync(output,{recursive:true});const fixture=path.join(output,'modules/Microsoft.Graph.Authentication/99.0.0');fs.mkdirSync(fixture,{recursive:true});
 const module=fs.readFileSync(path.join(root,'tests/test_outlook_powershell.py'),'utf8').split("MODULE=r'''")[1].split("'''")[0];
 fs.writeFileSync(path.join(fixture,'Microsoft.Graph.Authentication.psm1'),module);
 fs.writeFileSync(path.join(fixture,'Microsoft.Graph.Authentication.psd1'),"@{RootModule='Microsoft.Graph.Authentication.psm1';ModuleVersion='99.0.0';GUID='879297cc-155b-4cba-a395-a12a576fd100';FunctionsToExport='*'}");
 // The same portable-runtime layout used in production, so MCP discovers pwsh.
 const tools=path.join(output,'microsoft-tools');fs.mkdirSync(tools,{recursive:true});if(!fs.existsSync(path.join(tools,'powershell')))fs.symlinkSync(path.dirname(pwsh),path.join(tools,'powershell'),process.platform==='win32'?'junction':'dir');
 let page=await launch();check('packaged_application',await app.evaluate(({app})=>app.isPackaged));await status(page).filter({hasText:'未连接'}).waitFor();
 check('no_microsoft_password_field',await page.getByLabel('微软密码',{exact:true}).count()===0);
 check('settings_has_no_business_query_button',await page.getByRole('button',{name:/本周未读|最近12小时/}).count()===0);
 await page.getByRole('button',{name:'连接 Outlook',exact:true}).click();await status(page).filter({hasText:'已连接'}).waitFor();check('connect_from_visible_settings',true);
 check('body_read_consent_explained',(await page.locator('.outlook-settings').innerText()).includes('Mail.Read'));
 await page.locator('.outlook-settings').screenshot({path:path.join(output,'outlook-connected.png')});
 if(process.env.BOKKIO_TEST_API_KEY){
  await page.evaluate(v=>window.bokkio.api('/api/settings',v),{api_key:process.env.BOKKIO_TEST_API_KEY,base_url:process.env.BOKKIO_TEST_BASE_URL,model:process.env.BOKKIO_TEST_MODEL,jev_enabled:false,workspace:path.join(output,'workspace')});
  fs.mkdirSync(path.join(output,'workspace'),{recursive:true});await page.reload();
  await chat(page,'统计最近24小时收到且目前未读的邮件数量，范围是整个邮箱。给出具体数量及查询时间范围。','unread24h',s=>/2\s*(封|条)/.test(s));
  await page.evaluate(()=>window.bokkio.api('/api/settings',{jev_enabled:true}));
  await chat(page,'汇总最近12小时收到的邮件内容，包括已读和未读邮件，范围是整个邮箱。逐封列出主题、关键事项、数字或时间及负责人，不要仅复述主题。','summary12h',s=>s.includes('22:00')&&s.includes('林舟')&&s.includes('730')&&!s.includes('Old archive'));
  await chat(page,'找出最近24小时 release@example.invalid 发来的邮件，概括正文并列出主题。','sender24h',s=>s.includes('Release handoff')&&s.includes('Earlier note')&&!s.includes('Budget review'));
  const requests=fs.readFileSync(path.join(fixture,'requests.jsonl'),'utf8').trim().split(/\r?\n/).map(s=>JSON.parse(s));
  check('real_model_uses_dynamic_graph_requests',requests.some(r=>decodeURIComponent(r.uri).includes('isRead'))&&requests.some(r=>decodeURIComponent(r.uri).includes('body'))&&requests.some(r=>decodeURIComponent(r.uri).includes('release@example.invalid')));
  check('real_model_follows_graph_pagination',requests.some(r=>r.uri.includes('fixture_offset=')));
  const {DatabaseSync}=require('node:sqlite');const db=new DatabaseSync(path.join(output,'runtime/runtime.sqlite3'),{readOnly:true});
  const calls=db.prepare('SELECT tool,status FROM operations').all();db.close();
  check('api_tasks_do_not_invoke_native_selection',calls.filter(c=>c.tool==='outlook.request'&&c.status==='completed').length>=3&&!calls.some(c=>c.tool.startsWith('desktop.')));
  report.model_chat='three real Harness tasks against offline mail data';
 }
 await page.getByRole('button',{name:'Shortcuts',exact:true}).click();
 await page.getByRole('button',{name:'创建空 Workflow',exact:true}).click();await page.getByRole('button',{name:'插入步骤',exact:true}).click();
 await page.getByLabel('拾取应用').locator('option').nth(1).waitFor({state:'attached'});check('native_app_discovery_loads_when_picker_opens',true);
 await page.locator('.modal').getByRole('button',{name:'×',exact:true}).click();
 await app.close();app=null;page=await launch();await status(page).filter({hasText:'已连接'}).waitFor();check('connection_identity_rechecked_after_app_restart',true);
 const profile=JSON.parse(fs.readFileSync(path.join(output,'runtime/outlook-connection.json')));check('profile_contains_only_identity_fields',Object.keys(profile).sort().join(',')==='account,scopes,tenant'&&profile.scopes.includes('Mail.Read'));
 await page.getByRole('button',{name:'退出 Graph 登录',exact:true}).click();await status(page).filter({hasText:'未连接'}).waitFor();check('logout_removes_bokkio_profile',!fs.existsSync(path.join(output,'runtime/outlook-connection.json')));
 await app.close();app=null;page=await launch(true);await status(page).filter({hasText:'未连接'}).waitFor();
 await page.getByRole('button',{name:'连接 Outlook',exact:true}).click();await status(page).filter({hasText:'等待微软确认'}).waitFor();check('device_challenge_visible',(await page.getByLabel('微软设备码').textContent())==='OWNEDTEST');
 await page.getByRole('button',{name:'取消连接',exact:true}).click();await status(page).filter({hasText:'已取消'}).waitFor();check('login_cancel_stops_waiting_process',true);
 await page.getByRole('button',{name:'录制',exact:true}).click();check('cancelled_login_does_not_block_navigation',await page.getByRole('button',{name:'开始录制',exact:true}).isVisible());
})().catch(async error=>{report.error=error.stack;process.exitCode=1;console.error(error.message);if(app){const page=app.windows()[0];report.visible_outlook_state=await page.locator('.outlook-settings').innerText({timeout:1000}).catch(()=> 'window closed');await page.screenshot({path:path.join(output,'outlook-failure.png')}).catch(()=>{});}}).finally(async()=>{if(app)await app.close();fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));});
