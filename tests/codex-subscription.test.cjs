'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {EventEmitter}=require('node:events');
const {PassThrough,Writable}=require('node:stream');
const {runCodexSubscription,checkCodexAuth,_test}=require('../vendor/codex-subscription.cjs');

function mock(options={}) {
  const requests=[];let killed=false;
  const child=new EventEmitter();child.stdout=new PassThrough();child.stderr=new PassThrough();
  if(options.pid)child.pid=options.pid;
  const emit=message=>child.stdout.write(JSON.stringify(message)+'\n');
  child.stdin=new Writable({write(chunk,_,callback){
    const request=JSON.parse(chunk.toString());requests.push(request);
    callback();
    if(!Object.hasOwn(request,'id'))return;
    queueMicrotask(()=>{
      if(Object.hasOwn(options,'protocolValue')){emit(options.protocolValue);return;}
      if(options.hang===request.method)return;
      let result;
      switch(request.method){
        case 'initialize':result={userAgent:`codex_cli_rs/${options.version??'0.153.4'} (Mac OS)`};break;
        case 'account/read':result={account:{type:options.auth??'chatgpt',email:'private@example.com'}};break;
        case 'config/read':result=options.snapshot??{config:{mcp_servers:{external:{command:'secret-command'}}},layers:[{name:{type:'user'}}]};break;
        case 'configRequirements/read':result=options.managed??{requirements:null};break;
        case 'thread/start':result={thread:{id:'thread-test'}};break;
        case 'mcpServerStatus/list':result=options.inventory??{data:[{name:'external',tools:{},serverInfo:null}],nextCursor:null};break;
        case 'turn/start':
          if(options.nativeRequest){emit({id:77,method:'item/commandExecution/requestApproval',params:{}});return;}
          if(options.stderr){child.stderr.write(options.stderr);return;}
          emit({method:'item/completed',params:{threadId:'thread-test',item:options.item??{type:'agentMessage',text:options.text??'{"text":"hello","toolCalls":[]}'}}});
          emit({method:'turn/completed',params:{threadId:'thread-test',turn:{status:options.status??'completed'}}});
          result={turn:{id:'turn-test'}};break;
        default:throw new Error(request.method);
      }
      if(options.rpcError===request.method)emit({id:request.id,error:{message:'SECRET PROVIDER TOKEN'}});
      else emit({id:request.id,result});
    });
  }});
  child.kill=()=>{killed=true;return true;};
  return {requests,get killed(){return killed;},spawnImpl(binary,args,opts){
    if(Object.hasOwn(options,'expectedDetached'))assert.equal(opts.detached,options.expectedDetached);
    assert.equal(opts.shell,false);assert.ok(args.includes('force_login_method="chatgpt"'));
    assert.equal(opts.env.OPENAI_API_KEY,undefined);assert.equal(opts.env.OPENAI_BASE_URL,undefined);
    assert.equal(opts.env.NODE_OPTIONS,undefined);
    assert.ok(args.includes('features={ '+Object.entries(Object.fromEntries(Object.keys(_test.SAFE_CONFIG).filter(k=>k.startsWith('features.')).map(k=>[k.slice(9),false]))).map(([k,v])=>`${k} = ${v}`).join(', ')+' }'));
    return child;
  }};
}
const input={messages:[{role:'user',content:'Hello'}],tools:[]};

test('CLI-owned lifecycle keeps native children in the caller group and kills only child PID',async()=>{
  const calls=[];
  const originalKill=process.kill;
  process.kill=(pid,signal)=>{calls.push({pid,signal});return true;};
  try {
    const cli=mock({expectedDetached:false,pid:999999});
    await checkCodexAuth({...cli,detached:false});
    assert.ok(cli.killed);assert.deepEqual(calls,[]);
    const host=mock({expectedDetached:process.platform!=='win32',pid:999999});
    await checkCodexAuth(host);
    if(process.platform!=='win32')assert.deepEqual(calls,[{pid:-999999,signal:'SIGKILL'}]);
    else assert.ok(host.killed);
    const step=mock({expectedDetached:false,pid:999998});
    await runCodexSubscription({...step,...input,detached:false});
    assert.ok(step.killed);
    assert.equal(calls.length,process.platform==='win32'?0:1);
  } finally {process.kill=originalKill;}
});

test('null, arrays, and primitive protocol frames fail closed without throwing from data handler',async()=>{
  for(const protocolValue of [null,[],[{}],true,false,0,42,'secret']) {
    const m=mock({protocolValue});
    await assert.rejects(checkCodexAuth(m),/invalid protocol/);
    assert.ok(m.killed);
  }
});

test('native ChatGPT auth checked without returning account details',async()=>{
  const m=mock();assert.deepEqual(await checkCodexAuth({...m,env:{PATH:'/bin',OPENAI_API_KEY:'secret',OPENAI_BASE_URL:'https://bad',NODE_OPTIONS:'--require=/bad'}}),{subscription:true});
  assert.ok(m.killed);assert.deepEqual(m.requests.map(r=>r.method),['initialize','initialized','account/read']);
});
test('API-key auth and unsupported versions fail closed',async()=>{
  for(const settings of [{auth:'apiKey'},{auth:null,version:'0.154.0'},{version:'0.153.40'}]) {
    const m=mock(settings);await assert.rejects(checkCodexAuth(m),/subscription/);assert.ok(m.killed);
  }
});
test('one step uses no native environment, MCP, dynamic tools, or project instructions',async()=>{
  const m=mock();assert.deepEqual(await runCodexSubscription({...m,...input}),{text:'hello',toolCalls:[]});
  const thread=m.requests.find(r=>r.method==='thread/start').params;
  assert.deepEqual(thread.environments,[]);assert.deepEqual(thread.dynamicTools,[]);
  assert.equal(thread.config['features.shell_tool'],false);assert.equal(thread.config.project_doc_max_bytes,0);
  assert.deepEqual(thread.config.mcp_servers,{external:{enabled:false}});
  assert.equal(thread.ephemeral,true);assert.equal(thread.modelProvider,'openai');
  const turn=m.requests.find(r=>r.method==='turn/start').params;
  assert.deepEqual(turn.environments,[]);assert.deepEqual(turn.outputSchema,_test.OUTPUT_SCHEMA);
  assert.ok(m.killed);
});
test('known Grok tool proposals are returned without local execution',async()=>{
  const m=mock({text:'{"text":"","toolCalls":[{"name":"read_file","arguments":"{\\"path\\":\\"note.txt\\"}"}]}'});
  const result=await runCodexSubscription({...m,...input,tools:[{type:'function',function:{name:'read_file'}}]});
  assert.equal(result.toolCalls[0].name,'read_file');
});
test('image content travels inline with transcript positions and tool results retained',()=>{
  const result=_test.prepareInput([{role:'user',content:[{type:'image_url',image_url:{url:'data:image/png;base64,AA=='}}]},{role:'tool',tool_call_id:'a',content:'result'}],[]);
  assert.equal(result[1].type,'image');assert.match(result[0].text,/Attached image 1/);assert.match(result[0].text,/tool_call_id/);
  assert.throws(()=>_test.prepareInput([{content:[{type:'image_url',image_url:{url:'file:///secret'}}]}],[]),/inline/);
});
test('managed hooks/features and unknown or legacy layers denied before thread creation',async()=>{
  for(const settings of [
    {managed:{requirements:{managedHooks:{SessionStart:[{command:'secret'}]}}}},
    {managed:{requirements:{featureRequirements:{shell_tool:true}}}},
    {snapshot:{config:{},layers:[{name:{type:'legacyManagedConfigTomlFromFile'}}]}},
    {snapshot:{config:{model_providers:{openai:{base_url:'https://secret'}}},layers:[]}},
  ]) {
    const m=mock(settings);await assert.rejects(runCodexSubscription({...m,...input}),/subscription/);
    assert.ok(!m.requests.some(r=>r.method==='thread/start'));
  }
});
test('active MCP inventory stops before inference',async()=>{
  const m=mock({inventory:{data:[{name:'external',tools:{execute:{}},serverInfo:{}}]}});
  await assert.rejects(runCodexSubscription({...m,...input}),/not disabled/);
  assert.ok(!m.requests.some(r=>r.method==='turn/start'));
});
test('missing or duplicated MCP attestation is rejected; unrelated provider config is permitted',async()=>{
  for(const data of [[],[{name:'external',tools:{},serverInfo:null},{name:'external',tools:{},serverInfo:null}]]) {
    const m=mock({inventory:{data}});
    await assert.rejects(runCodexSubscription({...m,...input}),/not disabled/);
  }
  const m=mock({snapshot:{config:{model_providers:{unrelated:{base_url:'https://unused'}}},layers:[]},inventory:{data:[]}});
  assert.equal((await runCodexSubscription({...m,...input})).text,'hello');
});
test('native approvals or unexpected tool activity never succeed',async()=>{
  for(const setting of [{nativeRequest:true},{item:{type:'commandExecution',command:'secret'}}]) {
    const m=mock(setting);await assert.rejects(runCodexSubscription({...m,...input}),/unexpected native/);assert.ok(m.killed);
  }
});
test('malformed structured output and unknown or invalid tool proposals fail closed',async()=>{
  for(const text of ['not json','{"text":"ok","toolCalls":[],"extra":true}',
    '{"text":"ok","toolCalls":[{"name":"shell","arguments":"{}"}]}',
    '{"text":"ok","toolCalls":[{"name":"read_file","arguments":"[]"}]}']) {
    const m=mock({text});await assert.rejects(runCodexSubscription({...m,...input,tools:[{function:{name:'read_file'}}]}),/subscription/);
  }
});
test('provider and stderr errors stay content-free and bounded',async()=>{
  const m=mock({rpcError:'turn/start'});
  await assert.rejects(runCodexSubscription({...m,...input}),e=>!/SECRET/.test(e.message));
  const noisy=mock({stderr:'SECRET'.repeat(1000)});
  await assert.rejects(runCodexSubscription({...noisy,...input,maxOutputBytes:3000}),/output limit/);
});
test('cancellation and deadline kill the native process',async()=>{
  const controller=new AbortController();const m=mock({hang:'account/read'});
  const pending=checkCodexAuth({...m,signal:controller.signal});setTimeout(()=>controller.abort(),20);
  await assert.rejects(pending,/cancelled/);assert.ok(m.killed);
  const hanging=mock({hang:'initialize'});await assert.rejects(checkCodexAuth({...hanging,timeoutMs:20}),/deadline/);assert.ok(hanging.killed);
});
