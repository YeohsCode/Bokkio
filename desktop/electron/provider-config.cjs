const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
// Bokkio's existing planner uses OpenRouter. Never forward its key to another host.
function localProviderConfig({configPath=process.env.BOKKIO_PLANNER_CONFIG,platform=process.platform,home=os.homedir(),localAppData=process.env.LOCALAPPDATA}={}){
 const file=configPath||path.join(platform==='win32'?(localAppData||path.join(home,'AppData','Local')):platform==='darwin'?path.join(home,'Library','Application Support'):(process.env.XDG_CONFIG_HOME||path.join(home,'.config')),platform==='linux'?'bokkio':'Bokkio','planner.json');
 try{
  const value=JSON.parse(fs.readFileSync(file,'utf8'));
  if(!value||typeof value.api_key!=='string'||!value.api_key.trim())return null;
  if(value.base_url&&value.base_url.replace(/\/+$/,'')!=='https://openrouter.ai/api/v1')return null;
  return {api_key:value.api_key.trim(),base_url:'https://openrouter.ai/api/v1'};
 }catch{return null;}
}
module.exports={localProviderConfig};
