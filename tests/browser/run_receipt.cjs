const {spawn}=require('node:child_process');
const fs=require('node:fs');
const port=8877;
const base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.HW_TEST_PYTHON || 'python',['backend/tests/browser_server.py'],{env:{...process.env,HW_TEST_PORT:String(port)},stdio:'ignore',windowsHide:true});
server.on('error',error=>{console.error(error);process.exitCode=1;});
(async()=>{
 try {
  fs.mkdirSync('.codex-review',{recursive:true});
  let ready=false;
  for(let i=0;i<100;i++) {
   if(server.exitCode!==null)throw new Error('Isolated browser server exited');
   try {const response=await fetch(base+'/health');if(response.ok){ready=true;break;}}catch{}
   await new Promise(resolve=>setTimeout(resolve,200));
  }
  if(!ready)throw new Error('Isolated browser server did not start');
  const test=spawn(process.execPath,['tests/browser/receipt.cjs'],{env:{...process.env,HW_TEST_URL:base},stdio:'inherit',windowsHide:true});
  process.exitCode=await new Promise((resolve,reject)=>{test.on('error',reject);test.on('exit',code=>resolve(code||0));});
 } finally {server.kill();}
})().catch(error=>{console.error(error);server.kill();process.exitCode=1;});
