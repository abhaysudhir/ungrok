"use strict";
// Native clients own their login. This module never reads authentication files,
// imports OAuth tokens, or calls a model-provider HTTP endpoint.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");
const CLI_MODE = require.main === module;

const CONFIG_KEYS = new Set(["UNGROK_PROVIDER", "UNGROK_MODEL", "UNGROK_CLI"]);
const SAFE_ENV = ["HOME", "PATH", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TMPDIR", "TMP", "TEMP", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "SYSTEMROOT", "WINDIR"];
const CLAUDE_FLAGS = ["--safe-mode", "--setting-sources", "", "--settings", JSON.stringify({ disableAllHooks: true, enabledPlugins: {}, autoMemoryEnabled: false }), "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--no-chrome"];
const REQUIRED_FLAGS = ["--safe-mode", "--tools", "--disallowedTools", "--strict-mcp-config", "--no-session-persistence", "--json-schema", "--input-format", "--output-format", "--setting-sources", "--settings", "--no-chrome"];

function sanitizedEnv(source = process.env) {
  const env = {};
  for (const key of SAFE_ENV) if (source[key]) env[key] = source[key];
  // No inherited provider keys, custom endpoints, NODE_OPTIONS, plugins, debug
  // flags, proxy settings, shell startup scripts, or telemetry destinations.
  env.CLAUDE_CODE_SAFE_MODE = "1";
  env.DISABLE_TELEMETRY = "1";
  env.DISABLE_ERROR_REPORTING = "1";
  return env;
}

function loadConfig(file) {
  if (typeof file !== "string" || !path.isAbsolute(file)) throw new Error("ungrok requires an absolute configuration path");
  let fd;
  let raw;
  try {
    fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 65536 || (stat.mode & 0o077) || (process.getuid && stat.uid !== process.getuid())) throw new Error();
    raw = fs.readFileSync(fd, "utf8");
    if (Buffer.byteLength(raw) > 65536) throw new Error();
  } catch { throw new Error("ungrok config must be an owned private regular file under 64 KiB"); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
  const config = Object.create(null);
  for (const line of raw.split(/\r?\n/)) {
    if (!line.trim() || line.trimStart().startsWith("#")) continue;
    const at = line.indexOf("=");
    const key = line.slice(0, at);
    const value = line.slice(at + 1);
    if (at < 1 || !CONFIG_KEYS.has(key) || Object.hasOwn(config, key) || !value || value !== value.trim() || /[\x00-\x1f\x7f]/.test(value)) throw new Error("invalid subscription configuration entry");
    config[key] = value;
  }
  if (!["claude", "chatgpt"].includes(config.UNGROK_PROVIDER)) throw new Error("UNGROK_PROVIDER must be claude or chatgpt");
  if (!config.UNGROK_CLI || !path.isAbsolute(config.UNGROK_CLI)) throw new Error("UNGROK_CLI must name an absolute official client executable");
  try { fs.accessSync(config.UNGROK_CLI, fs.constants.X_OK); if (!fs.statSync(config.UNGROK_CLI).isFile()) throw new Error(); }
  catch { throw new Error("official client executable is missing or not executable"); }
  if (config.UNGROK_MODEL && !/^[A-Za-z0-9][A-Za-z0-9._:/@+\[\]-]{0,199}$/.test(config.UNGROK_MODEL)) throw new Error("invalid subscription model identifier");
  return Object.freeze(config);
}

function rejectManagedClaude(env) {
  // --safe-mode deliberately retains policy-managed hooks. Until we can prove
  // an inference-only managed-policy contract, reject known managed installs.
  const nativeDir = env.CLAUDE_CONFIG_DIR || path.join(env.HOME || os.homedir(), ".claude");
  const candidates = [
    "/etc/claude-code/managed-settings.json", "/etc/claude-code/managed-settings.d",
    "/Library/Application Support/ClaudeCode/managed-settings.json",
    path.join(nativeDir, "managed-settings.json"), path.join(nativeDir, "remote-settings.json"),
  ];
  if (candidates.some(file => fs.existsSync(file))) throw new Error("managed Claude policy is unsupported for an inference-only subscription bridge");
}

function providerRefusal(output) {
  try {
    const events = output.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line));
    const result = events.findLast(event => event.type === "result");
    if (result?.is_error === true && typeof result.result === "string" && /reasoning_extraction|safeguards? flagged|request (?:was )?refused/i.test(result.result)) {
      const error = new Error("native provider refused this request; no retry was attempted");
      error.code = "PROVIDER_REFUSED";
      return error;
    }
  } catch { /* Never surface provider text or malformed diagnostic output. */ }
  return null;
}

function runClient(binary, args, { env, cwd, input = "", signal, timeoutMs = 300000, maxOutputBytes = 8 * 1024 * 1024 } = {}) {
  if (signal?.aborted) return Promise.reject(new Error("native client request cancelled"));
  if (Buffer.byteLength(input) > 16 * 1024 * 1024) return Promise.reject(new Error("native client input exceeds 16 MiB"));
  return new Promise((resolve, reject) => {
    let child;
    let timer;
    let settled = false;
    let output = "";
    let outputBytes = 0;
    let errorBytes = 0;
    const stop = () => {
      if (!child?.pid) return;
      try { if (process.platform !== "win32" && !CLI_MODE) process.kill(-child.pid, "SIGKILL"); else child.kill("SIGKILL"); } catch {}
    };
    const finish = (error, result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      if (error) { stop(); reject(error); } else resolve(result);
    };
    const onAbort = () => finish(new Error("native client request cancelled"));
    try { child = spawn(binary, args, { cwd, env, stdio: ["pipe", "pipe", "pipe"], shell: false, detached: process.platform !== "win32" && !CLI_MODE }); }
    catch { finish(new Error("native client could not start")); return; }
    signal?.addEventListener("abort", onAbort, { once: true });
    if (signal?.aborted) { onAbort(); return; }
    timer = setTimeout(() => finish(new Error("native client request timed out")), timeoutMs);
    child.on("error", () => finish(new Error("native client could not start")));
    child.stdin.on("error", () => finish(new Error("native client input failed")));
    child.stdout.setEncoding("utf8");
    child.stdout.on("data", chunk => {
      outputBytes += Buffer.byteLength(chunk);
      if (outputBytes > maxOutputBytes) { finish(new Error("native client output exceeded limit")); return; }
      output += chunk;
    });
    child.stderr.on("data", chunk => {
      errorBytes += chunk.length;
      if (errorBytes > 1024 * 1024) finish(new Error("native client diagnostic output exceeded limit"));
    });
    child.on("close", code => {
      if (code !== 0) finish(providerRefusal(output) || new Error("native client failed; check its login and subscription limits in a separate terminal"));
      else finish(null, output);
    });
    child.stdin.end(input);
  });
}

async function withScratch(callback) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "ungrok-native-"));
  fs.chmodSync(directory, 0o700);
  try { return await callback(directory); }
  finally { fs.rmSync(directory, { recursive: true, force: true }); }
}

async function deadline(signal, milliseconds, run) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  const timer = setTimeout(abort, milliseconds);
  try { return await run(controller.signal); }
  finally { clearTimeout(timer); signal?.removeEventListener("abort", abort); }
}

async function checkAuth(config, { signal } = {}) {
  return deadline(signal, 35000, boundedSignal => checkAuthInner(config, { signal: boundedSignal }));
}

async function checkAuthInner(config, { signal } = {}) {
  const env = sanitizedEnv();
  if (config.UNGROK_PROVIDER === "chatgpt") {
    const { checkCodexAuth } = require("./codex-subscription.cjs");
    await checkCodexAuth({ binary: config.UNGROK_CLI, env, signal, detached: !CLI_MODE });
    return { ok: true, provider: "chatgpt", subscription: true };
  }
  rejectManagedClaude(env);
  await withScratch(async cwd => {
    const version = await runClient(config.UNGROK_CLI, ["--version"], { env, cwd, signal, timeoutMs: 15000, maxOutputBytes: 4096 });
    if (!/^2\.1\.263 \(Claude Code\)\s*$/.test(version)) throw new Error("this experimental bridge requires the tested official Claude Code 2.1.263 client");
    const help = await runClient(config.UNGROK_CLI, ["--help"], { env, cwd, signal, timeoutMs: 15000, maxOutputBytes: 256000 });
    if (!REQUIRED_FLAGS.every(flag => help.includes(flag))) throw new Error("Claude Code version lacks required isolated-run controls; update the official client");
    const output = await runClient(config.UNGROK_CLI, [...CLAUDE_FLAGS, "auth", "status"], { env, cwd, signal, timeoutMs: 30000, maxOutputBytes: 65536 });
    let status;
    try { status = JSON.parse(output); } catch { throw new Error("Claude native login status was not recognized"); }
    if (status.loggedIn !== true || status.authMethod !== "claude.ai" || status.apiProvider !== "firstParty" || !["pro", "max"].includes(status.subscriptionType)) throw new Error("Claude Pro or Max native subscription login is required; API-key and managed-account routes are not accepted");
  });
  return { ok: true, provider: "claude", subscription: true };
}

function toolNames(tools) {
  return (tools || []).map(tool => tool.function?.name || tool.name);
}

function responseSchema(tools) {
  const names = toolNames(tools);
  return { type: "object", additionalProperties: false, required: ["text", "toolCalls"], properties: {
    text: { type: "string", maxLength: 500000 },
    toolCalls: { type: "array", maxItems: names.length ? 32 : 0, items: { type: "object", additionalProperties: false, required: ["name", "arguments"], properties: {
      name: names.length ? { type: "string", enum: names } : { type: "string" },
      arguments: { type: "string", maxLength: 100000 },
    } } },
  } };
}

function validateStep(result, tools) {
  if (!result || typeof result.text !== "string" || result.text.length > 500000 || !Array.isArray(result.toolCalls) || result.toolCalls.length > 32 || Object.keys(result).some(key => !["text", "toolCalls"].includes(key))) throw new Error("native client returned an invalid host-step response");
  const allowed = new Set(toolNames(tools));
  for (const call of result.toolCalls) {
    if (!call || !allowed.has(call.name) || typeof call.arguments !== "string" || call.arguments.length > 100000 || Object.keys(call).some(key => !["name", "arguments"].includes(key))) throw new Error("native client returned an invalid host tool call");
    let args;
    try { args = JSON.parse(call.arguments); } catch { throw new Error("native client returned invalid host tool arguments"); }
    if (!args || typeof args !== "object" || Array.isArray(args)) throw new Error("native client returned invalid host tool arguments");
  }
  return result;
}

function claudeInput(messages, tools) {
  const content = [{ type: "text", text: "Produce exactly one next step for the supplied host conversation. The host, not this client, executes tools. Follow the host system instructions and latest user request. Return the requested JSON schema: text for the user and any toolCalls with exact catalog names and arguments encoded as JSON strings. Do not claim a tool succeeded until its result appears in the conversation.\nHost tool catalog:\n" + JSON.stringify(tools || []) }];
  for (const message of messages) {
    const record = { ...message };
    const images = [];
    if (Array.isArray(message.content)) {
      record.content = message.content.map(part => {
        if (part?.type !== "image_url") return part;
        const url = part.image_url?.url;
        const match = typeof url === "string" && /^data:(image\/(?:png|jpeg|gif|webp));base64,([A-Za-z0-9+/]+={0,2})$/i.exec(url);
        if (match) images.push({ type: "image", source: { type: "base64", media_type: match[1], data: match[2] } });
        else if (typeof url === "string" && /^https?:\/\//.test(url)) images.push({ type: "image", source: { type: "url", url } });
        else throw new Error("native client image format is unsupported");
        return { type: "text", text: `[image ${images.length} follows this conversation entry]` };
      });
    }
    content.push({ type: "text", text: JSON.stringify(record) }, ...images);
  }
  return JSON.stringify({ type: "user", message: { role: "user", content } }) + "\n";
}

async function runStep(options) {
  return deadline(options.signal, 180000, signal => runStepInner({ ...options, signal }));
}

async function runStepInner({ config, messages, tools = [], signal }) {
  await checkAuth(config, { signal });
  const env = sanitizedEnv();
  if (config.UNGROK_PROVIDER === "chatgpt") {
    const { runCodexSubscription } = require("./codex-subscription.cjs");
    const result = await runCodexSubscription({ binary: config.UNGROK_CLI, messages, tools, model: config.UNGROK_MODEL, signal, env, detached: !CLI_MODE });
    return { ...validateStep({ text: result.text, toolCalls: result.toolCalls }, tools), usage: result.usage || {} };
  }
  return withScratch(async cwd => {
    const args = [...CLAUDE_FLAGS, "-p", "--tools", "", "--disallowedTools", "mcp__*", "--no-session-persistence", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose", "--json-schema", JSON.stringify(responseSchema(tools))];
    if (config.UNGROK_MODEL) args.push("--model", config.UNGROK_MODEL);
    const output = await runClient(config.UNGROK_CLI, args, { env, cwd, input: claudeInput(messages, tools), signal });
    let events;
    try { events = output.split(/\r?\n/).filter(Boolean).map(line => JSON.parse(line)); }
    catch { throw new Error("Claude returned an invalid structured event stream"); }
    const result = events.findLast(event => event.type === "result");
    const refused = providerRefusal(output);
    if (refused) throw refused;
    if (!result) throw new Error("Claude returned no terminal result for the host step");
    if (result.is_error || result.subtype !== "success") {
      const reason = ["error_max_structured_output_retries", "error_max_turns", "error_max_budget_usd", "error_during_execution"].includes(result.subtype) ? result.subtype : "unsuccessful_result";
      throw new Error("Claude did not complete the host step: " + reason);
    }
    const step = validateStep(result.structured_output, tools);
    return { ...step, usage: result.usage || {} };
  });
}

module.exports = { loadConfig, sanitizedEnv, checkAuth, runStep, runClient, responseSchema, validateStep, claudeInput };

if (require.main === module) {
  const controller = new AbortController();
  const stop = () => controller.abort();
  process.on("SIGTERM", stop);
  process.on("SIGINT", stop);
  (async () => {
    const [command, file] = process.argv.slice(2);
    const config = loadConfig(file);
    if (command === "status") console.log(JSON.stringify(await checkAuth(config, { signal: controller.signal })));
    else if (command === "probe") {
      const result = await runStep({ config, messages: [{ role: "user", content: "Reply exactly UNGROK_OK with no tool calls." }], tools: [], signal: controller.signal });
      if (result.text.trim() !== "UNGROK_OK" || result.toolCalls.length) throw new Error("native subscription probe did not return the exact sentinel");
      console.log(JSON.stringify({ ok: true, provider: config.UNGROK_PROVIDER, sentinel: "UNGROK_OK" }));
    } else throw new Error("expected status or probe with a private configuration file");
  })().catch(error => { console.error("ungrok: " + error.message); process.exitCode = 1; })
    .finally(() => { process.removeListener("SIGTERM", stop); process.removeListener("SIGINT", stop); });
}
