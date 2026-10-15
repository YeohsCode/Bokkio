const {contextBridge,ipcRenderer}=require('electron');
const listen=(name,fn)=>{const handler=(_,data)=>fn(data);ipcRenderer.on(name,handler);return ()=>ipcRenderer.removeListener(name,handler);};
contextBridge.exposeInMainWorld('bokkio',{
 api:(route,data)=>ipcRenderer.invoke('api',route,data),settings:data=>ipcRenderer.invoke('settings',data),system:()=>ipcRenderer.invoke('system'),openWorkspace:()=>ipcRenderer.invoke('open-workspace'),
 recordStart:options=>ipcRenderer.invoke('record-start',options),recordStop:()=>ipcRenderer.invoke('record-stop'),recordPause:paused=>ipcRenderer.invoke('record-pause',paused),emergency:()=>ipcRenderer.invoke('emergency'),openPermissions:kind=>ipcRenderer.invoke('open-permissions',kind),
 overlayControl:control=>ipcRenderer.invoke('overlay-control',control),
 onControl:fn=>listen('shortcut-control',fn),onError:fn=>listen('runtime-error',fn),onOverlay:fn=>listen('overlay-state',fn)
});
