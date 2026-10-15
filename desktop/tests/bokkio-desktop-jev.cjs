const path=require('node:path'),os=require('node:os'),fs=require('node:fs'),assert=require('node:assert/strict');
const {_electron:electron}=require('playwright-core');const {spawnSync}=require('node:child_process');
const project=path.resolve(__dirname,'../..'),output=process.env.BOKKIO_TEST_OUTPUT||fs.mkdtempSync(path.join(os.tmpdir(),'bokkio-jev-'));
const python=process.env.BOKKIO_PYTHON||path.join(project,'.venv','bin/python'),editor=process.platform==='win32'?'notepad':'TextEdit',value='Bokkio Jev 三层链路验证';
let app;const report={checks:[],scope:'real_Harness_Jev_Runtime_native_editor'};
function check(name,value){assert(value,name);report.checks.push({name,passed:true});console.log(name);}
function actor(flag){const r=spawnSync(python,[path.join(project,'scripts/verify_desktop_native.py'),'--app',editor,'--output',path.join(output,'actor'),'--value',value,flag],{encoding:'utf8',timeout:60000,env:{...process.env,PYTHONPATH:path.join(project,'src'),PYTHONUTF8:'1'}});assert.equal(r.status,0,r.stdout+r.stderr);}
(async()=>{
 actor('--reset-only');
 app=await electron.launch({executablePath:process.env.BOKKIO_ELECTRON||require('electron'),args:[path.join(project,'desktop')],env:{...process.env,BOKKIO_DESKTOP_STATE:output},timeout:60000});
 const page=await app.firstWindow();page.setDefaultTimeout(30000);const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.waitForSelector('.rail');report.packaged=await app.evaluate(({app})=>app.isPackaged);
 await page.evaluate(v=>window.bokkio.api('/api/settings',v),{api_key:process.env.BOKKIO_TEST_API_KEY,base_url:process.env.BOKKIO_TEST_BASE_URL,model:process.env.BOKKIO_TEST_MODEL,...(process.env.BOKKIO_TEST_JEV_KEY?{jev_api_key:process.env.BOKKIO_TEST_JEV_KEY}:{}),...(process.env.BOKKIO_HARNESS_PYTHON?{harness_python:process.env.BOKKIO_HARNESS_PYTHON}:{}),workspace:path.join(output,'workspace')});
 await page.getByRole('button',{name:'配置',exact:true}).click();check('jev_configuration_visible',await page.getByRole('heading',{name:'Jev 局部决策',exact:true}).isVisible());
 await page.getByRole('button',{name:'对话',exact:true}).click();check('architecture_names_real_layers',(await page.locator('.work-head').textContent()).includes('原生界面局部决策：Jev'));
 await page.locator('.composer textarea').fill(`在 ${editor} 的当前唯一文档窗口执行：先将文档全文替换为“${value}”，然后对该文档按一次 Right 右箭头。只使用 Bokkio MCP，打开会话并查询实际窗口标题。两次交互都调用 desktop.step：第一次不要提供 input，使用原生控件能力，goal="Replace the entire document text with the allowed literal"、allowed_values 包含完整文本；第二次 goal="Press Right arrow in the document editor"、input={"action":"key","key":"Right"}。由 Jev 选择控件，读取实际结果再报告。不要保存文件，不调用代码，不使用 Workflow。`);
 await page.getByRole('button',{name:'执行任务',exact:true}).click();await page.waitForSelector('.conversation .execution-tree');
 await page.waitForFunction(()=>document.querySelector('.conversation .execution-tree')?.textContent.includes('Jev 局部决策')||['已完成','失败'].includes(document.querySelector('.task-card > .pill')?.textContent),null,{timeout:240000});
 await page.waitForFunction(()=>['已完成','失败','已取消'].includes(document.querySelector('.task-card > .pill')?.textContent),null,{timeout:360000});
 const chat=await page.evaluate(async()=>{const chats=await window.bokkio.api('/api/chats');return window.bokkio.api('/api/chat?id='+chats[0].id)});
 fs.writeFileSync(path.join(output,'trace.json'),JSON.stringify({id:chat.id,status:chat.status,response:chat.response,error:chat.error,trace:chat.trace},null,2));
 check('real_sdk_task_completed',chat.status==='completed');check('jev_actually_called',chat.trace.architecture.jev_active&&chat.trace.counts.jev_calls>=2);
 const decisions=chat.trace.children.filter(n=>n.engine==='Jev');check('two_real_jev_decisions',decisions.length>=2&&decisions.every(n=>n.decision_events.some(e=>e.kind==='decision.selected')));
 check('text_action_under_jev',decisions.some(n=>n.decision_events.some(e=>e.kind==='decision.selected'&&['set_value','type','replace_text'].includes(e.action))&&n.children.some(o=>['desktop.act','desktop.input'].includes(o.title)&&['verified','executed'].includes(o.status))));
 check('keyboard_input_under_jev',decisions.some(n=>n.children.some(o=>o.title==='desktop.input'&&o.status==='executed')));
 check('sdk_and_jev_correlate_by_operation_id',decisions.every(n=>n.call_id&&n.operation_id));
 check('readback_after_each_action',decisions.every(n=>n.children.filter(o=>o.title==='desktop.observe').length>=3));
 check('real_model_named',decisions.every(n=>n.decision_events.some(e=>e.kind==='decision.requested'&&e.model.includes('jev'))));
 actor('--read-only');check('independent_native_readback',true);
 await page.getByRole('button',{name:'全部展开',exact:true}).click();check('three_level_native_ui',await page.locator('li[data-layer="1"] > ol > li[data-layer="2"] > ol > li[data-layer="3"]').count()>0);
 check('ui_displays_jev_confidence',(await page.locator('.execution-tree').textContent()).includes('置信度'));
 await page.screenshot({path:path.join(output,'jev-tree.png')});await page.locator('[data-trace-id='+JSON.stringify(decisions[0].id)+']').screenshot({path:path.join(output,'jev-decision.png')});check('no_js_errors',!errors.length);
 report.jev_calls=chat.trace.counts.jev_calls;report.decisions=decisions.length;report.operations=chat.trace.counts.operations;console.log(JSON.stringify(report,null,2));
})().catch(e=>{report.error=e.stack;process.exitCode=1;console.error(e);}).finally(async()=>{fs.mkdirSync(output,{recursive:true});fs.writeFileSync(path.join(output,'report.json'),JSON.stringify(report,null,2));if(app)await app.close();});
