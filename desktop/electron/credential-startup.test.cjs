const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');

function host(t){
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'bokkio-credential-startup-'));t.after(()=>fs.rmSync(folder,{recursive:true,force:true}));fs.writeFileSync(path.join(folder,'provider-key.bin'),'encrypted-fixture');
 const handlers=new Map(),writes=[];let release,started;const decrypting=new Promise(resolve=>{started=resolve}),decryption=new Promise(resolve=>{release=resolve});
 const electron={app:{whenReady:()=>new Promise(()=>{}),on(){},getVersion:()=> 'test',getPath:()=>folder},ipcMain:{handle:(name,fn)=>handlers.set(name,fn)},safeStorage:{isAsyncEncryptionAvailable:async()=>true,decryptStringAsync:()=>{started();return decryption},encryptStringAsync:async()=>Buffer.from('encrypted'),decryptString(){throw Error('sync crypto blocks the UI')},isEncryptionAvailable(){throw Error('sync crypto blocks the UI')}},systemPreferences:{isTrustedAccessibilityClient:()=>true}};
 const context=vm.createContext({require:name=>name==='electron'?electron:require(name),process:{env:{},platform:'darwin',execPath:'/Applications/Bokkio.app/Contents/MacOS/Bokkio'},__dirname:path.resolve(__dirname),setInterval,clearInterval,setTimeout,clearTimeout,Buffer,fetch:async(url,request)=>{if(request.body)writes.push(JSON.parse(request.body));return {ok:true,json:async()=>String(url).includes('/api/permissions')?{accessibility:true}:{has_api_key:true}}}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'main.cjs'),'utf8'),context);vm.runInContext('stateRoot='+JSON.stringify(folder),context);
 return {handlers,writes,context,decrypting,release};
}

test('pending OS Keychain confirmation leaves settings and permission IPC responsive',async t=>{
 const value=host(t);const loading=vm.runInContext('loadCredentials()',value.context);await value.decrypting;
 assert.equal((await value.handlers.get('credential-state')()).status,'loading');
 assert.equal((await value.handlers.get('settings')(null)).has_api_key,true);
 assert.equal((await value.handlers.get('system')()).accessibility,true);
 value.release({result:'fixture-key',shouldReEncrypt:false});await loading;
 const state=await value.handlers.get('credential-state')();assert.equal(state.status,'ready');assert(!JSON.stringify(state).includes('fixture-key'));
});

test('saving a replacement key cannot be overwritten by a slower startup decryption',async t=>{
 const value=host(t);const loading=vm.runInContext('loadCredentials()',value.context);await value.decrypting;
 const save=value.handlers.get('settings')(null,{api_key:'replacement-key'});assert.equal(value.writes.length,0);
 value.release({result:'startup-key',shouldReEncrypt:false});await loading;await save;
 assert.equal(value.writes[0].api_key,'startup-key');assert.equal(value.writes.at(-1).api_key,'replacement-key');
});
