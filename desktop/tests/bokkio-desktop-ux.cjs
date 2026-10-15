// Scored mutations use visible UI controls and physical OS input only.
// No window.bokkio calls, API requests, seeded Workflow documents or Runtime actor.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {spawnSync}=require('node:child_process');const {_electron:electron}=require('playwright-core');
const project=path.resolve(__dirname,'../..');const output=path.resolve(process.env.BOKKIO_TEST_OUTPUT||path.join(project,'desktop/ux-results',String(Date.now())));
const state=path.join(output,'state');fs.mkdirSync(output,{recursive:true});
const windows=process.platform==='win32';const python=process.env.BOKKIO_PYTHON||path.join(project,'.desktop-venv/Scripts/python.exe');const actorBinary=process.env.BOKKIO_UX_ACTOR||path.join(output,'macos-ux-actor');const fixture=path.join(output,'Bokkio UX '+path.basename(output)+'.txt');const second=windows?'font':'calculator';
const report={contract:'visible_UI_only',platform:process.platform,checks:[],actions:[],errors:[]};let app,page,overlay;
function check(name,ok,detail){report.checks.push({name,passed:!!ok,...(detail?{detail}:{})});assert(ok,name);}
function actor(command,value){const request=JSON.stringify({command,value,window:path.basename(fixture)});const r=spawnSync(windows?python:actorBinary,windows?[path.join(__dirname,'windows-ux-actor.py'),request]:[request],{encoding:'utf8',timeout:20000});assert.equal(r.status,0,r.stdout+r.stderr);report.actions.push({surface:'native app',command,value,at:Date.now()});const observed=JSON.parse(r.stdout.trim());report.actions.at(-1).observed=observed;if(command==='editor')assert.equal(observed.editor,value,'Native editor input must actually take effect');if(command==='font')assert.equal(observed.font,value,'Native font selection must actually take effect');return observed;}
async function click(target,name){report.actions.push({surface:'Bokkio UI',name,at:Date.now()});await target.getByRole('button',{name,exact:true}).click();}
function drafts(){const folder=path.join(state,'workflow-drafts');return fs.existsSync(folder)?fs.readdirSync(folder).filter(p=>p.endsWith('.json')).map(p=>JSON.parse(fs.readFileSync(path.join(folder,p)))).sort((a,b)=>b.document.recording.started_at-a.document.recording.started_at):[];}
async function waitRead(fn,timeout=10000){const end=Date.now()+timeout;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch{}await new Promise(r=>setTimeout(r,100));}throw Error('Read-only evidence timed out');}
async function overlayVisible(){await waitRead(()=>app.evaluate(({BrowserWindow})=>BrowserWindow.getAllWindows().some(w=>w.getTitle()==='Bokkio 操作控制'&&w.isVisible())));}
async function evidence(name){await page.screenshot({path:path.join(output,name+'.png')});}
(async()=>{
 if(!windows){const built=spawnSync('swiftc',[path.join(__dirname,'macos-ux-actor.swift'),'-o',actorBinary],{encoding:'utf8',timeout:60000});assert.equal(built.status,0,built.stderr);fs.writeFileSync(fixture,'');spawnSync('open',['-a','TextEdit',fixture]);await waitRead(()=>actor('read'));actor('close-second');}
 // Reset only the dedicated test editor through its actual UI before recording.
 if(windows)actor('close-second');actor('editor','');
 app=await electron.launch({executablePath:process.env.BOKKIO_ELECTRON||require('electron'),args:[path.join(project,'desktop')],env:{...process.env,BOKKIO_DESKTOP_STATE:state,BOKKIO_DESKTOP_USER_DATA:path.join(output,'user-data')},timeout:60000});
 page=await app.firstWindow();page.setDefaultTimeout(15000);page.on('pageerror',e=>report.errors.push(e.message));await page.waitForSelector('.rail');
 await click(page,'新建 Workflow');check('new_workflow_has_no_app_picker',await page.getByRole('checkbox').count()===0);
 await page.getByLabel('Workflow 名称',{exact:true}).fill(windows?'UX · Notepad → Character Map → Notepad':'UX · TextEdit → Calculator → TextEdit');await evidence('01-create');
 await click(page,'开始录制');overlay=await waitRead(()=>app.windows().find(w=>w!==page));
 assert(overlay,'Floating control window exists');await overlayVisible();await overlay.waitForSelector('#pause');
 await overlay.locator('#status').filter({hasText:'正在录制操作'}).waitFor();
 actor('editor','Bokkio UX first');await waitRead(()=>drafts()[0]?.document.steps.some(s=>s.arguments?.value==='Bokkio UX first'));
 await click(overlay,'暂停');await overlay.locator('#status').filter({hasText:'录制已暂停'}).waitFor();
 const paused=await waitRead(()=>drafts().find(d=>d.status==='paused'));actor('editor','PAUSED INPUT MUST NOT APPEAR');
 check('paused_input_excluded',JSON.stringify(drafts()[0].document.steps)===JSON.stringify(paused.document.steps));
 await click(overlay,'继续');await overlay.locator('#status').filter({hasText:'正在录制操作'}).waitFor();
 actor('editor','Bokkio UX first');actor('open-second');actor(second,windows?'Courier New':undefined);actor('editor','Bokkio UX cross-app done');
 await overlay.screenshot({path:path.join(output,'02-floating-controls.png')});const started=Date.now();await click(overlay,'停止并编辑');
 await page.waitForSelector('.step-row');report.stop_ms=Date.now()-started;check('visible_stop_finishes',report.stop_ms<8000,{milliseconds:report.stop_ms});
 const draft=await waitRead(()=>drafts().find(d=>d.status==='stopped'));report.workflow=draft.document;report.issues=draft.issues;
 check('both_apps_automatically_recorded',Object.values(draft.document.apps).some(a=>a.name===(windows?'notepad':'TextEdit'))&&Object.values(draft.document.apps).some(a=>a.name===(windows?'charmap':'Calculator')));
 check('bokkio_controls_excluded',Object.values(draft.document.apps).every(a=>a.name!=='Bokkio'));
 check('no_capture_issues',draft.issues.length===0);check('paused_value_not_saved',!JSON.stringify(draft.document).includes('PAUSED INPUT'));
 const frozen=JSON.stringify(draft.document);actor('editor','AFTER STOP MUST NOT APPEAR');await new Promise(r=>setTimeout(r,400));check('stopped_recorder_cannot_append',JSON.stringify(drafts()[0].document)===frozen);
 const edited='Bokkio UX edited done';const lastEdit=draft.document.steps.map((s,i)=>s.action==='replace_text'?i:-1).filter(i=>i>=0).at(-1);
 await page.locator('.step-row').nth(lastEdit).click();await click(page,'内容');await page.getByLabel('文字 / 参数').fill(edited);
 await click(page,'保存');await page.locator('.work-head .tiny').filter({hasText:'已保存'}).waitFor();await evidence('03-saved');
 const id=draft.document.id;const saved=JSON.parse(fs.readFileSync(path.join(state,'workflows',id,'1.json')));check('saved_workflow_matches_recording',saved.steps.length===draft.document.steps.length);check('UI_edit_updates_value_and_completion_check',saved.steps[lastEdit].arguments.value===edited&&saved.steps[lastEdit].verify[0].equals===edited);report.saved_workflow=saved;
 // Reload from the library UI; no direct state injection.
 await click(page,'录制');await page.locator('.lib-item').filter({hasText:saved.name}).click();await page.waitForSelector('.step-row');
 actor('editor','');actor(windows?'font':'reset-second',windows?'Arial':undefined);
 await page.getByLabel('回放速度',{exact:true}).selectOption('5');await click(page,'回放');await overlayVisible();await overlay.locator('#status').filter({hasText:'正在回放'}).waitFor();
 await page.locator('.toolbar .pill').filter({hasText:/已完成|失败|执行结果未知/}).waitFor({timeout:90000});await evidence('04-replay');
 const actual=actor('read');report.actual=actual;const runs=fs.readdirSync(path.join(state,'workflow-runs')).filter(p=>p.endsWith('.json')).map(p=>JSON.parse(fs.readFileSync(path.join(state,'workflow-runs',p))));report.runs=runs;
 check('UI_replay_completed',runs.length===1&&runs[0].status==='completed',runs[0]?.error);
 check('real_editor_result',actual.editor===edited);check('real_second_app_result',windows?actual.font==='Courier New':actual.calculator==='9');
 await page.getByLabel('回放速度',{exact:true}).selectOption('0.5');await click(page,'从头回放');await page.locator('.toolbar .pill').filter({hasText:'执行中'}).waitFor();await overlayVisible();await overlay.locator('#status').filter({hasText:'正在回放'}).waitFor();
 await click(overlay,'暂停');await overlay.locator('#status').filter({hasText:'回放已暂停'}).waitFor({timeout:15000});check('replay_can_pause_from_floating_control',true);
 await click(overlay,'继续');await overlay.locator('#status').filter({hasText:'正在回放'}).waitFor();await click(overlay,'停止回放');
 await page.locator('.toolbar .pill').filter({hasText:'已取消'}).waitFor({timeout:15000});check('replay_can_stop_from_floating_control',true);
 const stopped=actor('read');await new Promise(r=>setTimeout(r,700));check('replay_stop_prevents_later_changes',JSON.stringify(actor('read'))===JSON.stringify(stopped));
 await click(page,'新建 Workflow');await click(page,'开始录制');await overlayVisible();actor('editor','Bokkio UX main stop');await click(overlay,'打开主界面');
 await click(page,'停止并编辑');await page.waitForSelector('.step-row');check('main_window_stop_finishes',drafts()[0].status==='stopped');
 await click(page,'新建 Workflow');await click(page,'开始录制');await overlayVisible();actor('editor','Bokkio UX emergency draft');await click(overlay,'打开主界面');
 await click(page,'紧急停止');await page.waitForSelector('.step-row');await waitRead(()=>drafts()[0]?.status==='stopped');
 check('emergency_preserves_captured_steps',drafts()[0].document.steps.some(s=>s.arguments?.value==='Bokkio UX emergency draft'));
 check('no_renderer_errors',report.errors.length===0);check('UX_scenario_completed',true);
 report.runs=fs.readdirSync(path.join(state,'workflow-runs')).filter(p=>p.endsWith('.json')).map(p=>JSON.parse(fs.readFileSync(path.join(state,'workflow-runs',p))));
})().catch(e=>{report.failure=e.stack;report.checks.push({name:'UX_scenario_completed',passed:false,detail:e.message});process.exitCode=1;console.error(e.stack);}).finally(async()=>{
 report.success=!report.failure&&report.checks.every(c=>c.passed);
 if(process.env.BOKKIO_ELECTRON){const executable=process.env.BOKKIO_ELECTRON;const resources=windows?path.join(path.dirname(executable),'resources'):path.resolve(path.dirname(executable),'../Resources');const archive=path.join(resources,'app.asar');if(fs.existsSync(archive))report.package_sha256=require('node:crypto').createHash('sha256').update(fs.readFileSync(archive)).digest('hex');}
 report.finished_at=new Date().toISOString();report.passed=report.checks.filter(c=>c.passed).length;report.total=report.checks.length;
 if(page)await evidence('final').catch(()=>{});fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({output,passed:report.passed,total:report.total,failure:report.failure},null,2));if(app)await app.close();
});
