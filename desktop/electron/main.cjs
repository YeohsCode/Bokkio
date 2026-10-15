const {app,BrowserWindow,ipcMain,desktopCapturer,globalShortcut,safeStorage,protocol,net,shell,systemPreferences,screen,Tray,Menu,nativeImage}=require('electron');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');
protocol.registerSchemesAsPrivileged([{scheme:'bokkio-media',privileges:{standard:true,secure:true,supportFetchAPI:true,stream:true}}]);
let mainWindow,overlay,captureWindow,service,endpoint,token,stateRoot,videoFile,videoId,videoStarted,videoStartedTick,videoFailure,selectedSource,pausedAt=0,pausedDuration=0;let quitting=false,activeRun=null,runWatch=null,watchEpoch=0,tray=null,badgeWatch=null;const shortcutStatus=[];let recordingTransition=Promise.resolve();
function mutateRecording(fn){const next=recordingTransition.catch(()=>{}).then(fn);recordingTransition=next.catch(()=>{});return next;}
async function globalControl(control){if(control==='emergency')return emergency();if(control==='pause'&&activeRun)return api('/api/runs/pause',{id:activeRun});return mutateRecording(async()=>{const state=await api('/api/record');if(control==='pause'){if(['recording','paused'].includes(state.status))notify({type:'recording-state',preview:await pauseRecording(state.status==='recording')});}else if(['recording','paused'].includes(state.status))notify({type:'recording-finished',preview:await finishRecording()});else notify('record');});}
function api(route,data){
 if(!/^\/api\/[a-z][a-z/-]*(\?.*)?$/.test(route))throw Error('Invalid API route');
 return fetch(endpoint+route,{method:data===undefined?'GET':'POST',headers:{'X-Bokkio-Token':token,'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)}).then(async r=>{const v=await r.json();if(!r.ok)throw Error(v.error||'Runtime request failed');return v;});
}
function credentialPath(){return path.join(app.getPath('userData'),'provider-key.bin');}
function readKey(){if(fs.existsSync(credentialPath())&&safeStorage.isEncryptionAvailable())return safeStorage.decryptString(fs.readFileSync(credentialPath()));return '';}
async function initializeService(){
 stateRoot=process.env.BOKKIO_DESKTOP_STATE||path.join(app.getPath('userData'),'runtime');fs.mkdirSync(stateRoot,{recursive:true,mode:0o700});
 const root=path.resolve(__dirname,'../..');
 const executable=app.isPackaged?path.join(process.resourcesPath,'runtime','python',process.platform==='win32'?'python.exe':'bin/python3'):(process.env.BOKKIO_PYTHON||path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'));
 const args=['-m','bokkio.desktop_service','--state',stateRoot];
 service=spawn(executable,args,{cwd:app.isPackaged?process.resourcesPath:root,env:{...process.env,BOKKIO_DESKTOP_PID:String(process.pid),PYTHONUNBUFFERED:'1',PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',...(!app.isPackaged?{PYTHONPATH:path.join(root,'src')}: {})},stdio:['ignore','pipe','pipe'],windowsHide:true});
 await new Promise((resolve,reject)=>{let buffer='';const timer=setTimeout(()=>reject(Error('Runtime did not start within 45 seconds')),45000);service.once('error',reject);service.once('exit',code=>{clearTimeout(timer);reject(Error('Runtime exited: '+code));});service.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){let line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{let data=JSON.parse(line);if(data.ready){endpoint=data.url;token=data.token;clearTimeout(timer);resolve();}}catch{}}});});
 service.stderr.on('data',()=>{});service.on('exit',()=>{if(!quitting&&mainWindow)mainWindow.webContents.send('runtime-error','Runtime stopped; reopen Bokkio to reconnect.');});
 const key=readKey();if(key)await api('/api/settings',{api_key:key});
}
function secureWindow(extra={}){return new BrowserWindow({width:1440,height:950,minWidth:1024,minHeight:700,backgroundColor:'#101317',title:'Bokkio',icon:path.join(__dirname,'../assets/icon.png'),...extra,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,...extra.webPreferences}});}
function notify(event){if(mainWindow&&!mainWindow.isDestroyed())mainWindow.webContents.send('shortcut-control',event);}
async function stopCapture(){
 if(!captureWindow)return null;
 await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Video finalization timed out')),10000);ipcMain.once('capture-finalized',()=>{clearTimeout(timer);resolve();});captureWindow.webContents.send('capture-control','stop');});
 captureWindow.destroy();captureWindow=null;if(videoFile){fs.closeSync(videoFile);videoFile=null;}
 if(videoFailure)throw Error(videoFailure);
 const ended=Date.now()/1000,tick=performance.now()/1000;const duration=Math.max(0,tick-videoStartedTick-pausedDuration-(pausedAt?tick-pausedAt:0));require('./webm.cjs').finishWebm(path.join(stateRoot,'recordings',videoId+'.webm'),duration*1000);
 const metadata={video_id:videoId,started_at:videoStarted,ended_at:ended,duration,source:selectedSource.name};fs.writeFileSync(path.join(stateRoot,'recordings',videoId+'.json'),JSON.stringify(metadata));return metadata;
}
async function emergency(){let preview=null;const failures=[];const state=await api('/api/record').catch(()=>null);if(state?.document&&['recording','paused','failed'].includes(state.status))preview=await mutateRecording(finishRecording).catch(e=>{failures.push(e.message);return null;});await api('/api/emergency-stop',{}).catch(e=>failures.push(e.message));await stopCapture().catch(e=>failures.push(e.message));clearInterval(badgeWatch);if(overlay&&!overlay.isDestroyed())overlay.hide();if(mainWindow&&!mainWindow.isDestroyed()&&!quitting)mainWindow.show();if(preview)notify({type:'recording-finished',preview});if(failures.length){const error=new Error('停止失败：'+failures.join('；'));mainWindow?.webContents.send('runtime-error',error.message);throw error;}notify('stopped');}
app.whenReady().then(async()=>{
 try{
 await initializeService();
 for(const [key,control] of [['CommandOrControl+Shift+R','record'],['CommandOrControl+Shift+P','pause'],['CommandOrControl+Shift+F12','emergency']])shortcutStatus.push({key,control,registered:globalShortcut.register(key,()=>globalControl(control).catch(e=>mainWindow?.webContents.send('runtime-error',e.message)))});
 protocol.handle('bokkio-media',request=>{const id=new URL(request.url).pathname.split('/').pop();if(!/^[a-f0-9]{32}\.webm$/.test(id||''))return new Response('Invalid media', {status:400});return net.fetch(require('node:url').pathToFileURL(path.join(stateRoot,'recordings',id)).toString());});
 mainWindow=secureWindow();mainWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));mainWindow.webContents.on('will-navigate',(e,url)=>{if(!url.startsWith('file://')&&!url.startsWith('http://127.0.0.1:5173'))e.preventDefault();});
 await mainWindow.loadFile(path.join(__dirname,'../dist/index.html'));
 tray=new Tray(nativeImage.createFromPath(path.join(__dirname,'../assets/icon.png')).resize({width:18,height:18}));tray.setToolTip('Bokkio Desktop Studio');tray.setContextMenu(Menu.buildFromTemplate([{label:'打开 Bokkio',click:()=>mainWindow.show()},{label:'暂停 / 继续录制',click:()=>globalControl('pause').catch(e=>mainWindow.webContents.send('runtime-error',e.message))},{label:'紧急停止',click:()=>emergency().catch(()=>{})}]));tray.on('click',()=>mainWindow.show());
 overlay=secureWindow({width:310,height:64,minWidth:310,minHeight:64,frame:false,transparent:true,alwaysOnTop:true,resizable:false,focusable:false,skipTaskbar:true,show:false});await overlay.loadFile(path.join(__dirname,'overlay.html'));overlay.setAlwaysOnTop(true,'floating');overlay.setIgnoreMouseEvents(true,{forward:true});const area=screen.getPrimaryDisplay().workArea;overlay.setPosition(area.x+Math.round((area.width-310)/2),area.y+8);
 mainWindow.on('close',e=>{if(!quitting){e.preventDefault();quitting=true;emergency().finally(()=>{service?.kill();app.quit();});}});
 }catch(error){require('electron').dialog.showErrorBox('Bokkio could not start',error.message);service?.kill();app.quit();}
});
app.on('window-all-closed',()=>{quitting=true;service?.kill();app.quit();});app.on('will-quit',()=>{globalShortcut.unregisterAll();service?.kill();});
function watchRun(id){
 activeRun=id;clearInterval(runWatch);const epoch=++watchEpoch;overlay.hide();tray?.setToolTip('Bokkio 正在回放 · Ctrl/⌘ ⇧ F12 停止');
 runWatch=setInterval(async()=>{try{const run=await api('/api/run?id='+id);if(epoch!==watchEpoch)return;if(!['running','ready'].includes(run.status)){clearInterval(runWatch);activeRun=null;if(!quitting&&!mainWindow.isDestroyed()){mainWindow.show();mainWindow.focus();}if(!overlay.isDestroyed())overlay.hide();tray?.setToolTip('Bokkio Desktop Studio');}}catch{if(epoch!==watchEpoch)return;clearInterval(runWatch);activeRun=null;if(!quitting&&!mainWindow.isDestroyed())mainWindow.show();}},400);
}
ipcMain.handle('api',async(_,route,data)=>{
 const replay=route==='/api/runs/start'||route==='/api/runs/resume';let headed=data?.mode!=='headless';
 if(route==='/api/runs/resume'){const run=await api('/api/run?id='+data.id);headed=run.mode==='headed';}
 if(replay&&headed){clearInterval(runWatch);watchEpoch++;mainWindow.hide();}
 try{const result=await api(route,data);if(replay&&headed)watchRun(result.id||data.id);return result;}catch(error){if(replay&&headed)mainWindow.show();throw error;}
});
ipcMain.handle('settings',async(_,data)=>{
 if(data?.api_key!==undefined){if(data.api_key&&!safeStorage.isEncryptionAvailable())throw Error('OS credential encryption is unavailable');if(data.api_key)fs.writeFileSync(credentialPath(),safeStorage.encryptString(data.api_key),{mode:0o600});else if(fs.existsSync(credentialPath()))fs.unlinkSync(credentialPath());}
 return api('/api/settings',data);
});
ipcMain.handle('open-recordings',()=>{const dir=path.join(stateRoot,'recordings');fs.mkdirSync(dir,{recursive:true});return shell.openPath(dir)});
ipcMain.handle('system',()=>({platform:process.platform,version:app.getVersion(),accessibility:process.platform==='darwin'?systemPreferences.isTrustedAccessibilityClient(false):true,screen_capture:process.platform==='darwin'?systemPreferences.getMediaAccessStatus('screen'):'OS controlled',credential_encryption:safeStorage.isEncryptionAvailable(),shortcuts:shortcutStatus}));
ipcMain.handle('open-permissions',(_,kind)=>shell.openExternal(kind==='accessibility'?'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility':'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'));
ipcMain.handle('sources',async()=>{const rows=await desktopCapturer.getSources({types:['screen','window'],thumbnailSize:{width:240,height:140},fetchWindowIcons:true});const own=new Set(BrowserWindow.getAllWindows().map(w=>w.getMediaSourceId()));return rows.filter(s=>!own.has(s.id)).map(s=>({id:s.id,name:s.name,thumbnail:s.thumbnail.toDataURL(),display_id:s.display_id}));});
async function beginRecording(options){
 if(captureWindow)throw Error('Recording is already active');videoFailure=null;pausedAt=0;pausedDuration=0;selectedSource=options.source;
 let metadata={};
 try{
 if(options.video!==false){
 const sources=await desktopCapturer.getSources({types:['screen','window']});const source=sources.find(s=>s.id===options.source?.id);if(!source)throw Error('屏幕采集尚未授权，请在配置页打开 macOS 录屏设置，授权 Bokkio 后重启。');
 videoId=crypto.randomBytes(16).toString('hex');fs.mkdirSync(path.join(stateRoot,'recordings'),{recursive:true,mode:0o700});videoFile=fs.openSync(path.join(stateRoot,'recordings',videoId+'.webm'),'wx',0o600);
 captureWindow=secureWindow({show:false,width:1,height:1,minWidth:1,minHeight:1,webPreferences:{backgroundThrottling:false}});
 captureWindow.webContents.session.setDisplayMediaRequestHandler((_,callback)=>callback({video:source,audio:undefined}));
 await captureWindow.loadFile(path.join(__dirname,'capture.html'));
 await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Screen capture did not start')),20000);const ready=()=>{clearTimeout(timer);ipcMain.removeListener('capture-error',failed);resolve();};const failed=(_,error)=>{clearTimeout(timer);ipcMain.removeListener('capture-ready',ready);reject(Error(error));};ipcMain.once('capture-ready',ready);ipcMain.once('capture-error',failed);captureWindow.webContents.send('capture-control','start');});
 videoStarted=Date.now()/1000;videoStartedTick=performance.now()/1000;metadata={video_id:videoId,started_at:videoStarted,source:source.name};
 }
 const result=await api('/api/record/start',{pids:options.pids,name:options.name});
 if(metadata.video_id){const saved={...metadata,event_offset:result.document.recording.started_at-metadata.started_at};await api('/api/draft/video',{id:result.document.id,metadata:saved});fs.writeFileSync(path.join(stateRoot,'recordings',videoId+'.json'),JSON.stringify({...saved,workflow_id:result.document.id,status:'recording'}));}
 overlay.showInactive();overlay.webContents.send('overlay-state','recording');tray?.setToolTip('Bokkio 正在录制 · Ctrl/⌘ ⇧ F12 停止');mainWindow.hide();clearInterval(badgeWatch);badgeWatch=setInterval(()=>{if(!overlay||overlay.isDestroyed())return;const p=screen.getCursorScreenPoint(),b=overlay.getBounds();if(p.x>b.x-60&&p.x<b.x+b.width+60&&p.y>b.y-60&&p.y<b.y+b.height+60)overlay.hide();else overlay.showInactive();},40);return {...result,video:metadata};
 }catch(error){await stopCapture().catch(()=>{});throw error;}
}
ipcMain.handle('record-start',(_,options)=>mutateRecording(()=>beginRecording(options)));
async function finishRecording(){const result=await api('/api/record/stop',{});const metadata=await stopCapture();clearInterval(badgeWatch);overlay.hide();tray?.setToolTip('Bokkio Desktop Studio');if(metadata){result.document.recording={...result.document.recording,...metadata};await api('/api/draft/video',{id:result.document.id,metadata:result.document.recording});}if(!quitting){mainWindow.show();mainWindow.focus();}return result;}
ipcMain.handle('record-stop',()=>mutateRecording(finishRecording));
async function pauseRecording(paused){const result=await api('/api/record/'+(paused?'pause':'resume'),{});if(paused)pausedAt=performance.now()/1000;else if(pausedAt){pausedDuration+=performance.now()/1000-pausedAt;pausedAt=0;}captureWindow?.webContents.send('capture-control',paused?'pause':'resume');overlay.webContents.send('overlay-state',paused?'paused':'recording');return result;}
ipcMain.handle('record-pause',(_,paused)=>mutateRecording(()=>pauseRecording(paused)));
ipcMain.handle('capture-chunk',(event,bytes)=>{if(event.sender!==captureWindow?.webContents)throw Error('Invalid capture sender');if(!videoFile)throw Error('No active video');try{fs.writeSync(videoFile,Buffer.from(bytes));}catch(error){videoFailure=error.message;emergency();throw error;}});
ipcMain.on('capture-error',(_,error)=>{videoFailure=error;notify('capture-error');});
ipcMain.handle('emergency',()=>emergency());
