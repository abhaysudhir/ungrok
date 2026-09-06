"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const runtime = require("../vendor/subscription-runtime.cjs");
const adapter = require("../vendor/xai-prompt-session.cjs");

function fixture(t, { mode = "success", model = "sonnet" } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ungrok-subscription-test-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const binary = path.join(dir, "claude");
  fs.writeFileSync(binary, `#!${process.execPath}
const args=process.argv.slice(2);
if(args.includes("--version")) { console.log("2.1.263 (Claude Code)"); process.exit(0); }
if(args.includes("--help")) { console.log("--safe-mode --tools --disallowedTools --strict-mcp-config --no-session-persistence --json-schema --input-format --output-format --setting-sources --settings --no-chrome"); process.exit(0); }
if(args.includes("status")) { console.log(JSON.stringify({loggedIn:true,authMethod:"claude.ai",apiProvider:"firstParty",subscriptionType:${JSON.stringify(mode === "api" ? null : "max")}})); process.exit(0); }
if(process.env.ANTHROPIC_API_KEY || process.env.OPENAI_API_KEY || process.env.NODE_OPTIONS || process.env.ANTHROPIC_BASE_URL) process.exit(4);
if(!args.includes("--safe-mode") || args[args.indexOf("--tools")+1]!=="" || args[args.indexOf("--disallowedTools")+1]!=="mcp__*") process.exit(5);
if(${JSON.stringify(mode)}==="hang") { setInterval(()=>{},1000); }
else {let raw="";process.stdin.on("data",c=>raw+=c);process.stdin.on("end",()=>{
 const input=JSON.parse(raw); const content=input.message.content;
 let value={text:"UNGROK_OK",toolCalls:[]};
 if(${JSON.stringify(mode)}==="tools") value={text:"Using host tool",toolCalls:[{name:"lookup",arguments:JSON.stringify({query:"test"})}]};
 if(${JSON.stringify(mode)}==="invalid") value={text:"bad",toolCalls:[{name:"forbidden",arguments:"{}"}]};
 if(${JSON.stringify(mode)}==="echo") value={text:JSON.stringify(content),toolCalls:[]};
 console.log(JSON.stringify({type:"result",subtype:"success",is_error:false,structured_output:value,usage:{input_tokens:3,output_tokens:2}}));
});}
`, { mode: 0o700 });
  const config = path.join(dir, "config.env");
  fs.writeFileSync(config, `UNGROK_PROVIDER=claude\nUNGROK_CLI=${binary}\nUNGROK_MODEL=${model}\n`, { mode: 0o600 });
  return { dir, binary, config };
}

test("subscription config is private immutable and rejects API settings", t => {
  const { config } = fixture(t);
  const loaded = runtime.loadConfig(config);
  assert.equal(loaded.UNGROK_PROVIDER, "claude");
  assert.ok(Object.isFrozen(loaded));
  fs.appendFileSync(config, "XAI_API_KEY=not-allowed\n");
  assert.throws(() => runtime.loadConfig(config), /invalid subscription/);
  assert.throws(() => runtime.loadConfig("relative"), /absolute/);
});

test("config rejects public permissions symlinks and duplicate fields", t => {
  const { config } = fixture(t);
  fs.chmodSync(config, 0o644);
  assert.throws(() => runtime.loadConfig(config), /private/);
  fs.chmodSync(config, 0o600);
  fs.symlinkSync(config, config + ".link");
  assert.throws(() => runtime.loadConfig(config + ".link"), /private/);
  fs.appendFileSync(config, "UNGROK_PROVIDER=claude\n");
  assert.throws(() => runtime.loadConfig(config), /invalid/);
});

test("environment allowlist drops provider credentials and executable injection", () => {
  const env = runtime.sanitizedEnv({ HOME: "/home/test", PATH: "/bin", ANTHROPIC_API_KEY: "secret", OPENAI_API_KEY: "secret", ANTHROPIC_BASE_URL: "https://bad", NODE_OPTIONS: "--require bad", BASH_ENV: "bad", HTTP_PROXY: "bad", CLAUDE_CODE_OAUTH_TOKEN: "secret", CODEX_HOME: "/native/account" });
  assert.equal(env.HOME, "/home/test");
  assert.equal(env.CODEX_HOME, "/native/account");
  for (const key of ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_BASE_URL", "NODE_OPTIONS", "BASH_ENV", "HTTP_PROXY", "CLAUDE_CODE_OAUTH_TOKEN"]) assert.ok(!(key in env));
});

test("native subscription status has no identity or credentials", async t => {
  const { config } = fixture(t);
  assert.deepEqual(await runtime.checkAuth(runtime.loadConfig(config)), { ok: true, provider: "claude", subscription: true });
});

test("non-subscription native auth is rejected without any model request", async t => {
  const { config } = fixture(t, { mode: "api" });
  await assert.rejects(runtime.checkAuth(runtime.loadConfig(config)), /subscription login/);
});

test("adapter preserves host contract and fixed configured model through tool result", async t => {
  const { config } = fixture(t, { mode: "tools" });
  const session = adapter.createXaiPromptSession({ envFile: config, requestedModel: "unrequested" });
  const executor = session.getExecutor([{ role: "user", content: "look up this" }]);
  const result = executor.stream({}, "request", [{ name: "lookup", parameters: { type: "object" } }]);
  const parts = [];
  for await (const part of result.fullStream) parts.push(part);
  assert.equal(session.getModelId(), "sonnet");
  const call = parts.find(part => part.type === "tool-call");
  assert.equal(call.toolName, "lookup");
  assert.deepEqual(call.args, { query: "test" });
  const response = await result.response;
  assert.equal(response.finishReason, "tool-calls");
  assert.equal(response.messages[0].content.find(part => part.type === "tool-call").toolCallId, call.toolCallId);
  executor.appendMessages(response.messages);
  executor.appendMessages({ role: "tool", tool_call_id: call.toolCallId, content: "found" });
  assert.equal(executor.getState().at(-1).content, "found");
  assert.equal((await result.usage).totalTokens, 5);
});

test("unknown host tools fail closed", async t => {
  const { config } = fixture(t, { mode: "invalid" });
  await assert.rejects(runtime.runStep({ config: runtime.loadConfig(config), messages: [{ role: "user", content: "hi" }], tools: [] }), /invalid host tool/);
});

test("Claude input preserves ordered images and full role-labelled tool history", () => {
  const input = JSON.parse(runtime.claudeInput([
    { role: "system", content: "rules" },
    { role: "user", content: [{ type: "text", text: "read" }, { type: "image_url", image_url: { url: "data:image/png;base64,AQID" } }] },
    { role: "assistant", tool_calls: [{ id: "x", function: { name: "lookup", arguments: "{}" } }] },
    { role: "tool", tool_call_id: "x", content: "result" },
  ], []));
  const content = input.message.content;
  assert.ok(content.some(part => part.type === "image" && part.source.data === "AQID"));
  assert.ok(content.some(part => part.text?.includes('"role":"system"')));
  assert.ok(content.some(part => part.text?.includes('"tool_call_id":"x"')));
});

module.exports = { fixture };
