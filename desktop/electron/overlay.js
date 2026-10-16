let busy=false;
window.bokkio.onOverlay(state=>{
 document.getElementById('status').textContent=({'paused':'Ⅱ 录制已暂停','replay':'▶ 正在回放','replay-paused':'Ⅱ 回放已暂停'})[state]||'● 正在录制操作';
 document.getElementById('pause').textContent=state.includes('paused')?'继续':'暂停';
 document.getElementById('stop').textContent=state.startsWith('replay')?'停止回放':'停止并编辑';
});
for(const control of ['pause','stop','show'])document.getElementById(control).addEventListener('click',async()=>{
 if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);
 try{await window.bokkio.overlayControl(control);document.getElementById('error').textContent='';}
 catch(error){document.getElementById('error').textContent=error.message;}
 finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}
});
