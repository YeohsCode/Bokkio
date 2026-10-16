const {app,BrowserWindow,ipcMain,globalShortcut,safeStorage,shell,clipboard,systemPreferences,screen,Tray,Menu,nativeImage}=require('electron');
const {spawn}=require('node:child_process');
const fs=require('node:fs');const path=require('node:path');
if(process.env.BOKKIO_DESKTOP_USER_DATA){const folder=path.resolve(process.env.BOKKIO_DESKTOP_USER_DATA);fs.mkdirSync(folder,{recursive:true});app.setPath('userData',folder);}
let mainWindow,overlay,service,endpoint,token,stateRoot;let quitting=false,activeRun=null,runWatch=null,watchEpoch=0,tray=null;const shortcutStatus=[];let recordingTransition=Promise.resolve();let overlayMode='recording';let credentialTransition=Promise.resolve(),credentialLoading=null,credentialEncryption=null;let credentials={status:'loading',error:''};
function mutateRecording(fn){const next=recordingTransition.catch(()=>{}).then(fn);recordingTransition=next.catch(()=>{});return next;}
async function globalControl(control){if(control==='emergency')return emergency();if(control==='pause'&&activeRun)return replayControl('pause');return mutateRecording(async()=>{const state=await api('/api/record');if(control==='pause'){if(['recording','paused'].includes(state.status))notify({type:'recording-state',preview:await pauseRecording(state.status==='recording')});}else if(['recording','paused','failed'].includes(state.status))notify({type:'recording-finished',preview:await finishRecording()});else if(control==='record')notify('record');});}
function api(route,data){
 if(!/^\/api\/[a-z][a-z/-]*(\?.*)?$/.test(route))throw Error('Invalid API route');
 return fetch(endpoint+route,{method:data===undefined?'GET':'POST',headers:{'X-Bokkio-Token':token,'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)}).then(async r=>{const v=await r.json();if(!r.ok)throw Error(v.error||'Runtime request failed');return v;});
}
function credentialPath(kind='provider'){return path.join(app.getPath('userData'),kind+'-key.bin');}
async function encryptionAvailable(){credentialEncryption=await safeStorage.isAsyncEncryptionAvailable();return credentialEncryption;}
async function readKey(kind='provider'){const file=credentialPath(kind);if(!fs.existsSync(file))return '';if(!await encryptionAvailable())throw Error('OS credential encryption is unavailable');return (await safeStorage.decryptStringAsync(fs.readFileSync(file))).result;}
async function writeKey(kind,value){const file=credentialPath(kind);if(value){if(!await encryptionAvailable())throw Error('OS credential encryption is unavailable');fs.writeFileSync(file,await safeStorage.encryptStringAsync(value),{mode:0o600});}else if(fs.existsSync(file))fs.unlinkSync(file);}
function credentialWork(fn){const next=credentialTransition.catch(()=>{}).then(fn);credentialTransition=next.catch(()=>{});return next;}
function credentialState(value){credentials=value;if(mainWindow&&!mainWindow.isDestroyed())mainWindow.webContents.send('credentials-state',credentials);}
function loadCredentials(){
 if(credentialLoading)return credentialLoading;
 credentialState({status:'loading',error:''});
 credentialLoading=credentialWork(async()=>{
  let key=await readKey();
  if(!key&&!fs.existsSync(path.join(stateRoot,'desktop-settings.json'))){
   const imported=require('./provider-config.cjs').localProviderConfig();
   if(imported){await writeKey('provider',imported.api_key);await api('/api/settings',imported);key=imported.api_key;}
  }
  const jevKey=await readKey('jev');if(key||jevKey)await api('/api/settings',{...(key?{api_key:key}:{}),...(jevKey?{jev_api_key:jevKey}:{})});
  credentialState({status:'ready',error:''});return credentials;
 }).catch(()=>{credentialState({status:'failed',error:'无法解锁保存的模型凭据。请完成系统钥匙串确认后重试。'});return credentials;}).finally(()=>{credentialLoading=null;});
 return credentialLoading;
}
async function initializeService(){
 stateRoot=process.env.BOKKIO_DESKTOP_STATE||path.join(app.getPath('userData'),'runtime');fs.mkdirSync(stateRoot,{recursive:true,mode:0o700});
 const root=path.resolve(__dirname,'../..');
 const executable=app.isPackaged?path.join(process.resourcesPath,'runtime','python',process.platform==='win32'?'python.exe':'bin/python3'):(process.env.BOKKIO_PYTHON||path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python'));
 const args=['-m','bokkio.desktop_service','--state',stateRoot];
 service=spawn(executable,args,{cwd:app.isPackaged?process.resourcesPath:root,env:{...process.env,BOKKIO_DESKTOP_PID:String(process.pid),BOKKIO_DESKTOP_APP_PATH:process.platform==='darwin'?path.resolve(process.execPath,'../../..'):path.dirname(process.execPath),PYTHONUNBUFFERED:'1',PYTHONDONTWRITEBYTECODE:'1',PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',...(!app.isPackaged?{PYTHONPATH:path.join(root,'src')}: {})},stdio:['ignore','pipe','pipe'],windowsHide:true});
 await new Promise((resolve,reject)=>{let buffer='';const timer=setTimeout(()=>reject(Error('Runtime did not start within 45 seconds')),45000);service.once('error',reject);service.once('exit',code=>{clearTimeout(timer);reject(Error('Runtime exited: '+code));});service.stdout.on('data',chunk=>{buffer+=chunk;let i;while((i=buffer.indexOf('\n'))>=0){let line=buffer.slice(0,i);buffer=buffer.slice(i+1);try{let data=JSON.parse(line);if(data.ready){endpoint=data.url;token=data.token;clearTimeout(timer);resolve();}}catch{}}});});
 service.stderr.on('data',()=>{});service.on('exit',()=>{if(!quitting&&mainWindow)mainWindow.webContents.send('runtime-error','Runtime stopped; reopen Bokkio to reconnect.');});

}
function secureWindow(extra={}){return new BrowserWindow({width:1440,height:950,minWidth:1024,minHeight:700,backgroundColor:'#101317',title:'Bokkio',icon:path.join(__dirname,'../assets/icon.png'),...extra,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,...extra.webPreferences}});}
function notify(event){if(mainWindow&&!mainWindow.isDestroyed())mainWindow.webContents.send('shortcut-control',event);}
async function emergency(){let preview=null;const failures=[];const state=await api('/api/record').catch(()=>null);if(state?.document&&['recording','paused','failed'].includes(state.status))preview=await mutateRecording(finishRecording).catch(e=>{failures.push(e.message);return null;});await api('/api/emergency-stop',{}).catch(e=>failures.push(e.message));if(overlay&&!overlay.isDestroyed())overlay.hide();if(mainWindow&&!mainWindow.isDestroyed()&&!quitting)mainWindow.show();if(preview)notify({type:'recording-finished',preview});if(failures.length){const error=new Error('停止失败：'+failures.join('；'));mainWindow?.webContents.send('runtime-error',error.message);throw error;}notify('stopped');}
app.whenReady().then(async()=>{
 try{
 await initializeService();
 for(const [key,control] of [['CommandOrControl+Shift+R','record'],['CommandOrControl+Shift+P','pause'],['CommandOrControl+Shift+F12','emergency']])shortcutStatus.push({key,control,registered:globalShortcut.register(key,()=>globalControl(control).catch(e=>mainWindow?.webContents.send('runtime-error',e.message)))});
 mainWindow=secureWindow();mainWindow.webContents.setWindowOpenHandler(()=>({action:'deny'}));mainWindow.webContents.on('will-navigate',(e,url)=>{if(!url.startsWith('file://')&&!url.startsWith('http://127.0.0.1:5173'))e.preventDefault();});
 await mainWindow.loadFile(path.join(__dirname,'../dist/index.html'));
 tray=new Tray(nativeImage.createFromPath(path.join(__dirname,'../assets/icon.png')).resize({width:18,height:18}));tray.setToolTip('Bokkio Desktop Studio');tray.setContextMenu(Menu.buildFromTemplate([{label:'打开 Bokkio',click:()=>mainWindow.show()},{label:'暂停 / 继续录制',click:()=>globalControl('pause').catch(e=>mainWindow.webContents.send('runtime-error',e.message))},{label:'停止录制并编辑',click:()=>globalControl('stop').catch(e=>mainWindow.webContents.send('runtime-error',e.message))},{label:'紧急停止',click:()=>emergency().catch(()=>{})}]));tray.on('click',()=>mainWindow.show());
 overlay=secureWindow({title:'Bokkio 操作控制',width:420,height:98,minWidth:420,minHeight:98,acceptFirstMouse:true,frame:false,transparent:true,alwaysOnTop:true,resizable:false,focusable:false,skipTaskbar:true,show:false});await overlay.loadFile(path.join(__dirname,'overlay.html'));overlay.setAlwaysOnTop(true,'floating');const area=screen.getPrimaryDisplay().workArea;overlay.setPosition(area.x+area.width-436,area.y+16);
 mainWindow.on('close',e=>{if(!quitting){e.preventDefault();quitting=true;emergency().finally(()=>{service?.kill();app.quit();});}});
 void loadCredentials();
 }catch(error){require('electron').dialog.showErrorBox('Bokkio could not start',error.message);service?.kill();app.quit();}
});
app.on('activate',()=>{if(mainWindow&&!mainWindow.isDestroyed())mainWindow.show();});
app.on('window-all-closed',()=>{quitting=true;service?.kill();app.quit();});app.on('will-quit',()=>{globalShortcut.unregisterAll();service?.kill();});
function watchRun(id){
 activeRun=id;clearInterval(runWatch);const epoch=++watchEpoch;overlayMode='replay';overlay.webContents.send('overlay-state','replay');overlay.showInactive();tray?.setToolTip('Bokkio 正在回放 · Ctrl/⌘ ⇧ F12 停止');
 runWatch=setInterval(async()=>{try{const run=await api('/api/run?id='+id);if(epoch!==watchEpoch)return;if(run.status==='paused'){overlay.webContents.send('overlay-state','replay-paused');mainWindow.show();return;}if(!['running','ready'].includes(run.status)){clearInterval(runWatch);activeRun=null;if(!quitting&&!mainWindow.isDestroyed()){mainWindow.show();mainWindow.focus();}if(!overlay.isDestroyed())overlay.hide();tray?.setToolTip('Bokkio Desktop Studio');}}catch{if(epoch!==watchEpoch)return;clearInterval(runWatch);activeRun=null;if(!quitting&&!mainWindow.isDestroyed())mainWindow.show();}},400);
}
ipcMain.handle('api',async(_,route,data)=>{
 const replay=route==='/api/runs/start'||route==='/api/runs/resume';let headed=data?.mode!=='headless';
 if(route==='/api/runs/resume'){const run=await api('/api/run?id='+data.id);headed=run.mode==='headed';}
 if(replay&&headed){clearInterval(runWatch);watchEpoch++;activeRun=null;overlay.hide();mainWindow.hide();}
 try{const result=await api(route,data);if(replay&&headed)watchRun(result.id||data.id);return result;}catch(error){if(replay&&headed)mainWindow.show();throw error;}
});
ipcMain.handle('credential-state',()=>credentials);
ipcMain.handle('unlock-credentials',()=>loadCredentials());
ipcMain.handle('settings',(_,data)=>data===undefined?api('/api/settings'):credentialWork(async()=>{
 for(const [field,kind] of [['api_key','provider'],['jev_api_key','jev']])if(data[field]!==undefined)await writeKey(kind,data[field]);
 const saved=await api('/api/settings',data);credentialState({status:'ready',error:''});return saved;
}));
ipcMain.handle('open-workspace',()=>shell.openPath(stateRoot));
ipcMain.handle('open-microsoft-login',()=>shell.openExternal('https://microsoft.com/devicelogin'));
ipcMain.handle('system',async()=>{const permissions=await api('/api/permissions'),hostTrusted=process.platform==='darwin'?systemPreferences.isTrustedAccessibilityClient(false):true;return {platform:process.platform,version:app.getVersion(),accessibility:permissions.accessibility,host_accessibility:hostTrusted,permission_issue:hostTrusted&&!permissions.accessibility?'runtime_identity':null,permissions,credential_encryption:credentialEncryption,shortcuts:shortcutStatus};});
ipcMain.handle('permission-action',async(_,action)=>{
 if(process.platform!=='darwin')throw Error('Accessibility setup is only needed on macOS');
 const permissions=await api('/api/permissions');
 if(action==='copy'){clipboard.writeText(permissions.authorization_path);return;}
 if(action==='reveal'){shell.showItemInFolder(permissions.authorization_path);return;}
 if(action==='request'){systemPreferences.isTrustedAccessibilityClient(true);await shell.openExternal(permissions.settings_url);return;}
 throw Error('Unknown permission action');
});
ipcMain.handle('open-permissions',(_,kind)=>{const panes={accessibility:'Privacy_Accessibility',input:'Privacy_ListenEvent',image:'Privacy_ScreenCapture'};if(process.platform!=='darwin'||!panes[kind])throw Error('Unknown system permission');return shell.openExternal('x-apple.systempreferences:com.apple.preference.security?'+panes[kind]);});
async function beginRecording(options){
 const result=await api('/api/record/start',{name:options.name});
 overlayMode='recording';overlay.webContents.send('overlay-state','recording');overlay.showInactive();tray?.setToolTip('Bokkio 正在录制操作');mainWindow.hide();return result;
}
ipcMain.handle('record-start',(_,options)=>mutateRecording(()=>beginRecording(options)));
async function finishRecording(){const result=await api('/api/record/stop',{});overlay.hide();tray?.setToolTip('Bokkio Desktop Studio');if(!quitting){mainWindow.show();mainWindow.focus();}return result;}
ipcMain.handle('record-stop',()=>mutateRecording(finishRecording));
async function pauseRecording(paused){const result=await api('/api/record/'+(paused?'pause':'resume'),{});overlay.webContents.send('overlay-state',paused?'paused':'recording');return result;}
ipcMain.handle('record-pause',(_,paused)=>mutateRecording(()=>pauseRecording(paused)));
ipcMain.handle('emergency',()=>emergency());

ipcMain.handle('overlay-control',async(event,control)=>{
 if(event.sender!==overlay.webContents||!['pause','stop','show'].includes(control))throw Error('Unknown recording control');
 try{
  if(control==='show'){mainWindow.show();return;}
  if(overlayMode==='replay'&&activeRun)return replayControl(control);
  return globalControl(control==='stop'?'stop':'pause');
 }catch(error){mainWindow.show();notify({type:'control-error',message:error.message});throw error;}
});

async function replayControl(control){
 if(control==='stop'){await api('/api/runs/cancel',{id:activeRun});overlay.hide();mainWindow.show();return;}
 const run=await api('/api/run?id='+activeRun);
 if(run.status==='paused'){mainWindow.hide();await api('/api/runs/resume',{id:activeRun});overlay.webContents.send('overlay-state','replay');}
 else await api('/api/runs/pause',{id:activeRun});
}
