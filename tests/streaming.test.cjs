"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const { runClient, sanitizedEnv } = require("../vendor/subscription-runtime.cjs");
const { createXaiPromptSession } = require("../vendor/xai-prompt-session.cjs");

function scratch(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ungrok-native-stream-test-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return directory;
}
test("native child cancellation settles without waiting for client output", async t => {
  const controller = new AbortController();
  const promise = runClient(process.execPath, ["-e", "setInterval(()=>{},1000)"], { env: sanitizedEnv(), cwd: scratch(t), signal: controller.signal });
  setTimeout(() => controller.abort(), 50);
  await assert.rejects(promise, /cancelled/);
});
test("runtime CLI termination cancels the active native child", { skip: process.platform === "win32" }, async t => {
  const cwd = scratch(t);
  const binary = path.join(cwd, "claude");
  const marker = path.join(cwd, "native.pid");
  fs.writeFileSync(binary, `#!${process.execPath}\nrequire('node:fs').writeFileSync(${JSON.stringify(marker)}, String(process.pid));setInterval(()=>{},1000);\n`, { mode: 0o700 });
  const config = path.join(cwd, "native.env");
  fs.writeFileSync(config, `UNGROK_PROVIDER=claude\nUNGROK_CLI=${binary}\n`, { mode: 0o600 });
  const child = spawn(process.execPath, [path.resolve(__dirname, "../vendor/subscription-runtime.cjs"), "status", config], { cwd, env: sanitizedEnv(), detached: true, stdio: "ignore" });
  const exited = new Promise(resolve => child.once("close", resolve));
  t.after(() => { try { process.kill(-child.pid, "SIGKILL"); } catch {} });
  const deadline = Date.now() + 5000;
  while (!fs.existsSync(marker) && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 20));
  assert.ok(fs.existsSync(marker), "native child started");
  const nativePid = Number(fs.readFileSync(marker, "utf8"));
  child.kill("SIGTERM");
  await Promise.race([exited, new Promise((_, reject) => { const timeout = setTimeout(() => reject(new Error("runtime CLI did not exit")), 5000); timeout.unref(); })]);
  assert.throws(() => process.kill(nativePid, 0), { code: "ESRCH" });
});
test("native child output limit and timeout are enforced without diagnostic leakage", async t => {
  const cwd = scratch(t);
  await assert.rejects(runClient(process.execPath, ["-e", "process.stdout.write('PRIVATE'.repeat(1000))"], { env: sanitizedEnv(), cwd, maxOutputBytes: 32 }), error => /exceeded limit/.test(error.message) && !error.message.includes("PRIVATE"));
  await assert.rejects(runClient(process.execPath, ["-e", "setInterval(()=>{},1000)"], { env: sanitizedEnv(), cwd, timeoutMs: 50 }), /timed out/);
  await assert.rejects(runClient(process.execPath, ["-e", "console.error('PRIVATE');process.exit(1)"], { env: sanitizedEnv(), cwd }), error => !error.message.includes("PRIVATE"));
});
test("pre-aborted native launch fails without executing client", async t => {
  const controller = new AbortController(); controller.abort();
  const marker = path.join(scratch(t), "must-not-exist");
  await assert.rejects(runClient(process.execPath, ["-e", "require('fs').writeFileSync(process.argv[1],'bad')", marker], { env: sanitizedEnv(), signal: controller.signal }), /cancelled/);
  assert.equal(fs.existsSync(marker), false);
});
test("provider refusal is surfaced without provider body or automatic retry", async t => {
  const text = "PRIVATE_CONTENT safeguards flagged this request: [reasoning_extraction]";
  const script = `console.log(JSON.stringify({type:'result',subtype:'success',is_error:true,result:${JSON.stringify(text)}}));process.exit(1)`;
  await assert.rejects(runClient(process.execPath, ["-e", script], { env: sanitizedEnv(), cwd: scratch(t) }), error => {
    assert.equal(error.code, "PROVIDER_REFUSED");
    assert.equal(error.message, "native provider refused this request; no retry was attempted");
    assert.ok(!error.message.includes("PRIVATE_CONTENT"));
    return true;
  });
});
test("host iterator return releases pending next and all metadata promises", async t => {
  const cwd = scratch(t);
  const binary = path.join(cwd, "claude");
  fs.writeFileSync(binary, `#!${process.execPath}
const args=process.argv.slice(2);
if(args.includes("--version")) console.log("2.1.263 (Claude Code)");
else if(args.includes("--help")) console.log("--safe-mode --tools --disallowedTools --strict-mcp-config --no-session-persistence --json-schema --input-format --output-format --setting-sources --settings --no-chrome");
else if(args.includes("status")) console.log(JSON.stringify({loggedIn:true,authMethod:"claude.ai",apiProvider:"firstParty",subscriptionType:"max"}));
else setInterval(()=>{},1000);
`, { mode: 0o700 });
  const config = path.join(cwd, "native.env");
  fs.writeFileSync(config, `UNGROK_PROVIDER=claude\nUNGROK_CLI=${binary}\n`, { mode: 0o600 });
  const stream = createXaiPromptSession({ envFile: config }).getExecutor([{role:"user",content:"hi"}]).stream({}, "id", []);
  const next = stream.fullStream.next();
  assert.equal((await stream.fullStream.return()).done, true);
  assert.equal((await next).done, true);
  const result = await Promise.all([stream.response, stream.usage, stream.extendedUsage, stream.providerMetadata, stream.invocationId]);
  assert.equal(result[0].finishReason, "error");
});
