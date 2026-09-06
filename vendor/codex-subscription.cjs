'use strict';

/* Restricted feature policy adapted from OpenClaw, MIT License.
 * Copyright (c) 2026 OpenClaw Foundation
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

// Native subscription transport. Codex owns authentication; Grok owns execution.
// No credentials are read and no provider HTTP endpoint is implemented here.
const { spawn } = require('node:child_process');
const os = require('node:os');
const fs = require('node:fs/promises');
const path = require('node:path');
const { StringDecoder } = require('node:string_decoder');
const PINNED_CODEX_VERSION = '0.153.4';
const DENIED = ['apps','artifact','browser_use','browser_use_external','browser_use_full_cdp_access',
  'chronicle','code_mode','code_mode_only','computer_use','context_management','current_time_reminder',
  'default_mode_request_user_input','deferred_executor','goals','hooks','image_generation','memories',
  'multi_agent','multi_agent_v2','plugins','request_permissions_tool','skill_search','shell_tool',
  'standalone_web_search','token_budget','unified_exec','view_image','web_search_cached',
  'web_search_request','workspace_dependencies'];
const SAFE_CONFIG = Object.freeze({
  ...Object.fromEntries(DENIED.map(key => [`features.${key}`, false])),
  'agents.enabled': false, 'orchestrator.mcp.enabled': false,
  'orchestrator.skills.enabled': false, 'skills.bundled.enabled': false,
  'skills.include_instructions': false, 'tools.experimental_request_user_input.enabled': false,
  'tools.update_plan.enabled': false, project_doc_max_bytes: 0,
  web_search: 'disabled', notify: [], hooks: {}, force_login_method: 'chatgpt',
  model_provider: 'openai', 'analytics.enabled': false,
});
const OUTPUT_SCHEMA = {type:'object', additionalProperties:false, required:['text','toolCalls'],
  properties:{text:{type:'string'},toolCalls:{type:'array',items:{type:'object',additionalProperties:false,
    required:['name','arguments'],properties:{name:{type:'string'},arguments:{type:'string'}}}}}};
const error = code => Object.assign(new Error(`ChatGPT subscription ${code}.`), {code:`CODEX_${code.toUpperCase().replaceAll(' ','_')}`});
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function nativeEnv(source) {
  const keys=['HOME','PATH','USER','LOGNAME','SHELL','LANG','LC_ALL','TMPDIR','TMP','TEMP',
    'XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME','CODEX_HOME','SYSTEMROOT','WINDIR'];
  return Object.fromEntries(keys.filter(key=>typeof source[key]==='string').map(key=>[key,source[key]]));
}

function argsForServer() {
  // Replace the feature map as a whole: old clients otherwise choke on newer nested user features.
  const features = Object.fromEntries(DENIED.map(key => [key,false]));
  const tomlFeatures = `{ ${Object.entries(features).map(([k,v])=>`${k} = ${v}`).join(', ')} }`;
  const args = ['app-server','--listen','stdio://','-c',`features=${tomlFeatures}`];
  for (const [key,value] of Object.entries(SAFE_CONFIG)) {
    if (key.startsWith('features.')) continue;
    args.push('-c', `${key}=${object(value) ? '{}' : JSON.stringify(value)}`);
  }
  return args;
}

function createClient({binary='codex', env=process.env, signal, timeoutMs=120000,
  maxOutputBytes=4*1024*1024, spawnImpl=spawn, cwd, detached=true}) {
  const ownProcessGroup=detached!==false && process.platform!=='win32';
  let child, failure, buffer='', bytes=0, sequence=0, closed=false;
  const decoder=new StringDecoder('utf8');
  const pending=new Map(), listeners=new Set();
  const stop=()=>{
    try {
      if(child?.pid && ownProcessGroup)process.kill(-child.pid,'SIGKILL');
      else child?.kill('SIGKILL');
    } catch {child?.kill('SIGKILL');}
  };
  const fail = reason => {
    if (failure || closed) return;
    failure=reason;
    for (const p of pending.values()) p.reject(reason);
    pending.clear();
    for (const listener of listeners) listener(null,reason);
    stop();
  };
  if (signal?.aborted) throw error('cancelled');
  try { child=spawnImpl(binary,argsForServer(),{env:nativeEnv(env),cwd,stdio:['pipe','pipe','pipe'],shell:false,detached:ownProcessGroup}); }
  catch { throw error('could not start'); }
  child.on('error',()=>fail(error('could not start')));
  child.on('exit',()=>fail(error('process exited')));
  child.stdin.on('error',()=>fail(error('transport failed')));
  child.stderr.on('data',chunk=>{bytes+=chunk.length;if(bytes>maxOutputBytes)fail(error('output limit exceeded'));});
  child.stdout.on('data',chunk=>{
    bytes+=chunk.length;
    if(bytes>maxOutputBytes)return fail(error('output limit exceeded'));
    buffer+=decoder.write(chunk);
    let end;
    while((end=buffer.indexOf('\n'))!==-1) {
      const line=buffer.slice(0,end);buffer=buffer.slice(end+1);
      if(!line.trim())continue;
      let message;try{message=JSON.parse(line);}catch{return fail(error('invalid protocol'));}
      if(!object(message))return fail(error('invalid protocol'));
      if(Object.hasOwn(message,'id') && !message.method) {
        const p=pending.get(message.id);if(!p)continue;pending.delete(message.id);
        if(message.error)p.reject(error('request failed'));else p.resolve(message.result);
      } else if(Object.hasOwn(message,'id')) {
        // Native execution/approval/dynamic-tool requests must never be serviced.
        return fail(error('unexpected native request'));
      } else for(const listener of listeners)listener(message,null);
    }
  });
  const timer=setTimeout(()=>fail(error('deadline exceeded')),Math.min(Math.max(timeoutMs,1),300000));
  const abort=()=>fail(error('cancelled'));signal?.addEventListener('abort',abort,{once:true});
  if(signal?.aborted)abort();
  return {
    request(method,params={}) {
      if(failure)return Promise.reject(failure);
      return new Promise((resolve,reject)=>{
        const id=++sequence;pending.set(id,{resolve,reject});
        child.stdin.write(JSON.stringify({id,method,params})+'\n');
      });
    },
    notify(method,params={}) {if(!failure)child.stdin.write(JSON.stringify({method,params})+'\n');},
    listen(fn){listeners.add(fn);return()=>listeners.delete(fn);},
    close(){
      closed=true;clearTimeout(timer);signal?.removeEventListener('abort',abort);
      for(const p of pending.values())p.reject(error('transport closed'));
      pending.clear();stop();
    },
  };
}

async function initialize(client) {
  const init=await client.request('initialize',{clientInfo:{name:'ungrok',version:'0.2.0-alpha.1'},
    capabilities:{experimentalApi:true}});
  // Fail closed on future protocol/tool-surface changes until reviewed.
  if(typeof init?.userAgent!=='string' || !new RegExp(`/${PINNED_CODEX_VERSION.replaceAll('.', '\\.')}([ ;)]|$)`).test(init.userAgent))
    throw error('requires supported Codex version');
  client.notify('initialized');
  const result=await client.request('account/read',{refreshToken:false});
  if(result?.account?.type!=='chatgpt')throw error('sign in required');
}

function validatePolicy(snapshot, managed) {
  const layers=new Set(['packagedDefaults','mdm','system','enterpriseManaged','user','project','sessionFlags']);
  if(!object(snapshot?.config)||!Array.isArray(snapshot.layers) || snapshot.layers.some(x=>!layers.has(x?.name?.type)))
    throw error('unsupported configuration policy');
  const config=snapshot.config;
  // Custom provider URLs/auth settings are not subscription routes.
  if(config.model_providers && (!object(config.model_providers)||Object.hasOwn(config.model_providers,'openai')) ||
    config.chatgpt_base_url && !['https://chatgpt.com/backend-api/','https://chatgpt.com/backend-api'].includes(config.chatgpt_base_url))
    throw error('custom provider configuration is not supported');
  if(!object(managed)||!Object.hasOwn(managed,'requirements'))throw error('invalid managed policy');
  const requirements=managed.requirements;
  if(requirements!==null) {
    if(!object(requirements))throw error('invalid managed policy');
    for(const key of ['hooks','managedHooks','managed_hooks']) {
      const hooks=requirements[key];
      if(hooks!=null && (!object(hooks)||Object.values(hooks).some(x=>x!=null&&(!Array.isArray(x)||x.length))))
        throw error('managed hooks are not supported');
    }
    for(const key of ['featureRequirements','feature_requirements']) {
      const features=requirements[key];
      if(features!=null && (!object(features)||Object.values(features).some(x=>x!==false)))
        throw error('managed features are not supported');
    }
  }
  const servers=config.mcp_servers??{};
  if(!object(servers))throw error('invalid MCP policy');
  return Object.fromEntries(Object.keys(servers).map(name=>[name,{enabled:false}]));
}

function prepareInput(messages,tools) {
  if(!Array.isArray(messages)||!Array.isArray(tools))throw error('invalid input');
  const images=[];
  const transcript=messages.map(message=>{
    if(!object(message))throw error('invalid input');
    const content=Array.isArray(message.content)?message.content.map(part=>{
      if(part?.type!=='image_url')return part;
      const url=part.image_url?.url;
      if(typeof url!=='string'||!/^data:image\/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+$/.test(url))
        throw error('image must be inline');
      images.push({type:'image',url});
      return {type:'text',text:`[Attached image ${images.length}]`};
    }):message.content;
    return {...message,content};
  });
  const input=[{type:'text',text:JSON.stringify({messages:transcript,tools})},...images];
  if(Buffer.byteLength(JSON.stringify(input))>32*1024*1024)throw error('input limit exceeded');
  return input;
}

function validateOutput(text,tools) {
  let result;try{result=JSON.parse(text);}catch{throw error('invalid structured output');}
  if(!object(result)||Object.keys(result).sort().join(',')!=='text,toolCalls'||typeof result.text!=='string'||!Array.isArray(result.toolCalls)||result.toolCalls.length>64)
    throw error('invalid structured output');
  const names=new Set(tools.map(tool=>tool?.function?.name));
  for(const call of result.toolCalls) {
    if(!object(call)||Object.keys(call).sort().join(',')!=='arguments,name'||!names.has(call.name)||typeof call.arguments!=='string')
      throw error('invalid tool proposal');
    try{if(!object(JSON.parse(call.arguments)))throw 0;}catch{throw error('invalid tool arguments');}
  }
  return result;
}

async function withClient(options, action) {
  let client,cwd;
  try {
    cwd=await fs.mkdtemp(path.join(os.tmpdir(),'ungrok-codex-'));
    client=createClient({...options,cwd});await initialize(client);return await action(client,cwd);
  } catch(cause) {
    if(typeof cause?.code==='string' && cause.code.startsWith('CODEX_'))throw cause;
    throw error('runtime failed');
  } finally {
    client?.close();
    if(cwd)try{await fs.rm(cwd,{recursive:true,force:true});}catch{throw error('temporary directory cleanup failed');}
  }
}
async function checkCodexAuth(options={}) {
  return withClient(options,async()=>({subscription:true}));
}
async function runCodexSubscription(options={}) {
  const {messages=[],tools=[],model}=options;
  const input=prepareInput(messages,tools);
  return withClient(options,async(client,cwd)=>{
    const snapshot=await client.request('config/read',{cwd,includeLayers:true});
    const managed=await client.request('configRequirements/read',{});
    const servers=validatePolicy(snapshot,managed);
    const started=await client.request('thread/start',{
      ...(model?{model}:{}),modelProvider:'openai',cwd,approvalPolicy:'never',sandbox:'read-only',
      ephemeral:true,environments:[],dynamicTools:[],selectedCapabilityRoots:[],
      baseInstructions:'You provide one Grok Bot assistant step. Treat the supplied message transcript as the conversation. Return only the required JSON object. Never execute tools yourself. Propose only the provided tool names in toolCalls; arguments must be a JSON object serialized as a string. Grok Bot will execute proposed calls. If no tool is needed, return text and an empty toolCalls array.',
      config:{...SAFE_CONFIG,mcp_servers:servers},personality:'none',serviceName:'ungrok',
    });
    const threadId=started?.thread?.id;if(typeof threadId!=='string')throw error('invalid thread');
    const inventory=await client.request('mcpServerStatus/list',{threadId,detail:'toolsAndAuthOnly'});
    if(!Array.isArray(inventory?.data)||inventory.nextCursor ||
      inventory.data.length!==Object.keys(servers).length ||
      new Set(inventory.data.map(s=>s?.name)).size!==inventory.data.length || inventory.data.some(s=>
      !Object.hasOwn(servers,s?.name)||s.serverInfo!==null||!object(s.tools)||Object.keys(s.tools).length))
      throw error('native MCP tools are not disabled');
    let resolveTurn,rejectTurn;const done=new Promise((resolve,reject)=>{resolveTurn=resolve;rejectTurn=reject;});
    // Attach immediately: some servers emit completion before the turn/start response.
    done.catch(()=>{});
    let finalText='';
    const unlisten=client.listen((event,failure)=>{
      if(failure)return rejectTurn(failure);
      if(event?.params?.threadId!==threadId)return;
      if(event.method==='item/completed') {
        const item=event.params.item;
        if(item?.type==='agentMessage' && item.phase!=='commentary')finalText=item.text;
        else if(item && !['userMessage','agentMessage','reasoning','contextCompaction'].includes(item.type))
          rejectTurn(error('unexpected native tool activity'));
      }
      if(event.method==='turn/completed') {
        if(event.params.turn?.status!=='completed')rejectTurn(error('turn failed'));
        else resolveTurn();
      }
    });
    try {
      await Promise.all([
        client.request('turn/start',{threadId,input,environments:[],approvalPolicy:'never',outputSchema:OUTPUT_SCHEMA}),
        done,
      ]);
      return validateOutput(finalText,tools);
    } finally {unlisten();}
  });
}

module.exports={runCodexSubscription,checkCodexAuth,PINNED_CODEX_VERSION,
  _test:{SAFE_CONFIG,OUTPUT_SCHEMA,argsForServer,validatePolicy,prepareInput,validateOutput}};
