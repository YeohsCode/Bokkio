let recorder,stream,pending=Promise.resolve(),failed=false;
window.bokkio.onCapture(async command=>{
 try{
 if(command==='start'){
 stream=await navigator.mediaDevices.getDisplayMedia({video:{frameRate:15},audio:false});
 const mime=MediaRecorder.isTypeSupported('video/webm;codecs=vp9')?'video/webm;codecs=vp9':'video/webm';recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2500000});
 recorder.ondataavailable=e=>{if(e.data.size)pending=pending.then(async()=>window.bokkio.captureChunk(await e.data.arrayBuffer())).catch(error=>{if(!failed){failed=true;window.bokkio.captureError(error.message);}});};
 recorder.onerror=e=>window.bokkio.captureError(e.error?.message||'Video encoding failed');
 recorder.onstop=()=>pending.finally(()=>{stream.getTracks().forEach(t=>t.stop());window.bokkio.captureFinalized();});
 stream.getVideoTracks()[0].onended=()=>{if(recorder.state!=='inactive'){window.bokkio.captureError('Capture source closed');recorder.stop();}};
 recorder.start(1000);window.bokkio.captureReady();
 }else if(command==='pause'&&recorder?.state==='recording')recorder.pause();
 else if(command==='resume'&&recorder?.state==='paused')recorder.resume();
 else if(command==='stop'){if(recorder&&recorder.state!=='inactive')recorder.stop();else window.bokkio.captureFinalized();}
 }catch(error){window.bokkio.captureError(error.message);}
});
