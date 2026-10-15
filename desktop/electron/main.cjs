const {app,BrowserWindow,ipcMain,globalShortcut,safeStorage,shell,systemPreferences,screen,Tray,Menu,nativeImage}=require('electron');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');
let mainWindow,overlay,service,endpoint,token,stateRoot;let quitting=false,activeRun=null,runWatch=null,watchEpoch=0,tray=null,badgeWatch=null;const shortcutStatus=[];let recordingTransition=Promise.resolve();
function mutateRecording(fn){const next=recordingTransition.catch(()=>{}).then(fn);recordingTransition=next.catch(()=>{});return next;}
async function globalControl(control){if(control==='emergency')return emergency();if(control==='pause'&&activeRun)return api('/api/runs/pause',{id:activeRun});return mutateRecording(async()=>{const state=await api('/api/record');if(control==='pause'){if(['recording','paused'].includes(state.status))notify({type:'recording-state',preview:await pauseRecording(state.status==='recording')});}else if(['recording','paused'].includes(state.status))notify({type:'recording-finished',preview:await finishRecording()});else notify('record');});}
function api(route,data){
 if(!/^\/api\/[a-z][a-z/-]*(\?.*)?$/.test(route))throw Error('Invalid API route');
 return fetch(endpoint+route,{method:data===undefined?'GET':'POST',headers:{'X-Bokkio-Token':token,'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)}).then(async r=>{const v=await r.json();if(!r.ok)throw Error(v.error||'Runtime request failed');return v;});
}
function credentialPath(kind='provider'){return path.join(app.getPath('userData'),kind+'-key.bin');}
function readKey(kind='provider'){if(fs.existsSync(credentialPath(kind))&&safeStorage.isEncryptionAvailable())return safeStorage.decryptString(fs.readFileSync(credentialPath(kind)));return '';}
async function initializeService(){
 stateRoot=process.env.BOKKIO_DESKTOP_STATE||path.join(app.getPath('userData'),'runtime');fs.mkdirSync(stateRoot,{recursive:true,mode:0o700});
 const root=path.resolve(__dirname,'../..');
 const executable=app.isPackaged?path.join(process.resourcesPath,'runtime','python',process.platform==='win32'?'python.exe':'bin/python3'):(process.env.BOKKIO_PYTHON||path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'));
 const args=['-m','bokkio.desktop_service','--state',stateRoot];
 service=spawn(executable,args,{cwd:app.isPackaged?process.resourcesPath:root,env:{...process.env,BOKKIO_DESKTOP_PID:String(process.pid),PYTHONUNBUFFERED:'1',PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',...(!app.isPackaged?{PYTHONPATH:path.join(root,'src')}: {})},stdio:['ignore','pipe','pipe'],windowsHide:true});
 await new Promise((resolve,reject)=>{let buffer='';const timer=setTimeout(()=>reject(Error('Runtime did not start within 45 seconds')),45000);service.once('error',reject);service.once('exit',code=>{clearTimeout(timer);reject(Error('Runtime exited: '+code));});service.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){let line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{let data=JSON.parse(line);if(data.ready){endpoint=data.url;token=data.token;clearTimeout(timer);resolve();}}catch{}}});});
 service.stderr.on('data',()=>{});service.on('exit',()=>{if(!quitting&&mainWindow)mainWindow.webContents.send('runtime-error','Runtime stopped; reopen Bokkio to reconnect.');});
 const key=readKey(),jevKey=readKey('jev');if(key||jevKey)await api('/api/settings',{...(key?{api_key:key}:{}),...(jevKey?{jev_api_key:jevKey}:{})});
}
function secureWindow(extra={}){return new BrowserWindow({width:1440,height:950,minWidth:1024,minHeight:700,backgroundColor:'#101317',title:'Bokkio',icon:path.join(__dirname,'../assets/icon.png'),...extra,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,...extra.webPreferences}});}
function notify(event){if(mainWindow&&!mainWindow.isDestroyed())mainWindow.webContents.send('shortcut-control',event);}
async function emergency(){let preview=null;const failures=[];const state=await api('/api/record').catch(()=>null);if(state?.document&&['recording','paused','failed'].includes(state.status))preview=await mutateRecording(finishRecording).catch(e=>{failures.push(e.message);return null;});await api('/api/emergency-stop',{}).catch(e=>failures.push(e.message));clearInterval(badgeWatch);if(overlay&&!overlay.isDestroyed())overlay.hide();if(mainWindow&&!mainWindow.isDestroyed()&&!quitting)mainWindow.show();if(preview)notify({type:'recording-finished',preview});if(failures.length){const error=new Error('停止失败：'+failures.join('；'));mainWindow?.webContents.send('runtime-error',error.message);throw error;}notify('stopped');}
app.whenReady().then(async()=>{
 try{
 await initializeService();
 for(const [key,control] of [['CommandOrControl+Shift+R','record'],['CommandOrControl+Shift+P','pause'],['CommandOrControl+Shift+F12','emergency']])shortcutStatus.push({key,control,registered:globalShortcut.register(key,()=>globalControl(control).catch(e=>mainWindow?.webContents.send('runtime-error',e.message)))});
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
 for(const [field,kind] of [['api_key','provider'],['jev_api_key','jev']]){if(data?.[field]!==undefined){const value=data[field],file=credentialPath(kind);if(value&&!safeStorage.isEncryptionAvailable())throw Error('OS credential encryption is unavailable');if(value)fs.writeFileSync(file,safeStorage.encryptString(value),{mode:0o600});else if(fs.existsSync(file))fs.unlinkSync(file);}}
 return api('/api/settings',data);
});
ipcMain.handle('open-workspace',()=>shell.openPath(stateRoot));
ipcMain.handle('system',()=>({platform:process.platform,version:app.getVersion(),accessibility:process.platform==='darwin'?systemPreferences.isTrustedAccessibilityClient(false):true,credential_encryption:safeStorage.isEncryptionAvailable(),shortcuts:shortcutStatus}));
ipcMain.handle('open-permissions',(_,kind)=>{const panes={accessibility:'Privacy_Accessibility',input:'Privacy_ListenEvent',image:'Privacy_ScreenCapture'};if(process.platform!=='darwin'||!panes[kind])throw Error('Unknown system permission');return shell.openExternal('x-apple.systempreferences:com.apple.preference.security?'+panes[kind]);});
async function beginRecording(options){
 const result=await api('/api/record/start',{pids:options.pids,name:options.name});
 overlay.showInactive();overlay.webContents.send('overlay-state','recording');tray?.setToolTip('Bokkio 正在录制操作 · Ctrl/⌘ ⇧ F12 停止');mainWindow.hide();clearInterval(badgeWatch);badgeWatch=setInterval(()=>{if(!overlay||overlay.isDestroyed())return;const p=screen.getCursorScreenPoint(),b=overlay.getBounds();if(p.x>b.x-60&&p.x<b.x+b.width+60&&p.y>b.y-60&&p.y<b.y+b.height+60)overlay.hide();else overlay.showInactive();},40);return result;
}
ipcMain.handle('record-start',(_,options)=>mutateRecording(()=>beginRecording(options)));
async function finishRecording(){const result=await api('/api/record/stop',{});clearInterval(badgeWatch);overlay.hide();tray?.setToolTip('Bokkio Desktop Studio');if(!quitting){mainWindow.show();mainWindow.focus();}return result;}
ipcMain.handle('record-stop',()=>mutateRecording(finishRecording));
async function pauseRecording(paused){const result=await api('/api/record/'+(paused?'pause':'resume'),{});overlay.webContents.send('overlay-state',paused?'paused':'recording');return result;}
ipcMain.handle('record-pause',(_,paused)=>mutateRecording(()=>pauseRecording(paused)));
ipcMain.handle('emergency',()=>emergency());
