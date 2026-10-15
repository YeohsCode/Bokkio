// Add finalized duration without loading the video into memory. MediaRecorder
// writes a Segment with unknown length and a finite Info block near the start.
const fs=require('node:fs');
function vint(buffer,offset){let width=1;while(width<=8&&!(buffer[offset]&(1<<(8-width))))width++;if(width>8||offset+width>buffer.length)throw Error('Invalid EBML length');let value=BigInt(buffer[offset]&((1<<(8-width))-1));for(let i=1;i<width;i++)value=(value<<8n)|BigInt(buffer[offset+i]);return {width,value,unknown:value===(1n<<BigInt(7*width))-1n};}
function writeVint(buffer,offset,width,value){if(value>=(1n<<BigInt(7*width))-1n)throw Error('EBML length overflow');for(let i=width-1;i>=0;i--){buffer[offset+i]=Number(value&255n);value>>=8n;}buffer[offset]|=1<<(8-width);}
function finishWebm(filename,durationMs){
 const fd=fs.openSync(filename,'r');const size=fs.fstatSync(fd).size;const header=Buffer.alloc(Math.min(size,65536));fs.readSync(fd,header,0,header.length,0);
 try{
 const segment=header.indexOf(Buffer.from([0x18,0x53,0x80,0x67]));const info=header.indexOf(Buffer.from([0x15,0x49,0xa9,0x66]));if(segment<0||info<0)throw Error('WebM metadata not found');const segmentSize=vint(header,segment+4),infoSize=vint(header,info+4);const payload=info+4+infoSize.width,end=payload+Number(infoSize.value);if(end>header.length||infoSize.unknown)throw Error('WebM Info exceeds header');
 const duration=Buffer.alloc(11);duration[0]=0x44;duration[1]=0x89;duration[2]=0x88;duration.writeDoubleBE(durationMs,3);
 writeVint(header,info+4,infoSize.width,infoSize.value+11n);if(!segmentSize.unknown)writeVint(header,segment+4,segmentSize.width,segmentSize.value+11n);
 const temporary=filename+'.finalizing';const out=fs.openSync(temporary,'wx',0o600);
 try{fs.writeSync(out,header.subarray(0,end));fs.writeSync(out,duration);const chunk=Buffer.alloc(1024*1024);let position=end;while(position<size){const count=fs.readSync(fd,chunk,0,Math.min(chunk.length,size-position),position);if(!count)throw Error('Video read stopped before EOF');fs.writeSync(out,chunk.subarray(0,count));position+=count;}fs.fsyncSync(out);}finally{fs.closeSync(out)}
 fs.closeSync(fd);fs.renameSync(temporary,filename);
 }catch(error){try{fs.closeSync(fd)}catch{}throw error;}
}
module.exports={finishWebm,vint,writeVint};
