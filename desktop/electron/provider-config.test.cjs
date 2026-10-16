const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {localProviderConfig}=require('./provider-config.cjs');
test('reuses Bokkio planner credentials only for OpenRouter, preserving the desktop model',t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'bokkio-config-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));const file=path.join(dir,'planner.json');
 fs.writeFileSync(file,JSON.stringify({api_key:'local-private-value',model:'openai/gpt-4.1',reasoning_effort:'high'}));assert.deepEqual(localProviderConfig({configPath:file}),{api_key:'local-private-value',base_url:'https://openrouter.ai/api/v1'});
 fs.writeFileSync(file,JSON.stringify({api_key:'local-private-value',base_url:'https://other.example/v1'}));assert.equal(localProviderConfig({configPath:file}),null);
 fs.writeFileSync(file,'broken');assert.equal(localProviderConfig({configPath:file}),null);assert.equal(localProviderConfig({configPath:path.join(dir,'absent')}),null);
});
test('finds the Bokkio configuration in both desktop platform locations',t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'bokkio-platform-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 for(const platform of ['darwin','win32']){const localAppData=path.join(dir,'local');const parent=platform==='darwin'?path.join(dir,'Library','Application Support','Bokkio'):path.join(localAppData,'Bokkio');fs.mkdirSync(parent,{recursive:true});fs.writeFileSync(path.join(parent,'planner.json'),JSON.stringify({api_key:'local-test-key'}));assert.equal(localProviderConfig({platform,home:dir,localAppData}).api_key,'local-test-key');}
});
