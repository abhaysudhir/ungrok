"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const { createXaiPromptSession, normalizeToolParameters } = require("../vendor/xai-prompt-session.cjs");

function fixture(t, base, extra = "") {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ungrok-adapter-test-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, "config.env");
  fs.writeFileSync(file, `XAI_API_KEY=TEST_SECRET\nSAND_XAI_BASE_URL=${base}\nSAND_XAI_MODEL=test-model\n${extra}`, { mode: 0o600 });
  return file;
}
async function server(t, handler) {
  const s = http.createServer(handler);
  await new Promise(resolve => s.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise(resolve => s.close(resolve)));
  return `http://127.0.0.1:${s.address().port}/v1`;
}
async function result(session, tools = []) {
  const ex = session.getExecutor([{ role: "user", content: "private prompt" }]);
  const stream = ex.stream({}, "test-request", tools);
  const parts = [];
  for await (const part of stream.fullStream) parts.push(part);
  return { parts, response: await stream.response, usage: await stream.usage, state: ex.getState() };
}

test("text, tools, auth and immutable per-session configuration", async t => {
  const requests = [];
  const base = await server(t, (req, res) => {
    let raw = "";
    req.on("data", chunk => { raw += chunk; });
    req.on("end", () => {
      requests.push({ body: JSON.parse(raw), auth: req.headers.authorization });
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      for (const event of [
        { choices: [{ delta: { content: "hello" } }] },
        { choices: [{ delta: { tool_calls: [{ index: 0, id: "call_1", function: { name: "lookup", arguments: '{"q":' } }] } }] },
        { choices: [{ delta: { tool_calls: [{ index: 0, function: { arguments: '"ok"}' } }] }, finish_reason: "tool_calls" }], usage: { prompt_tokens: 3, completion_tokens: 2 } },
      ]) res.write(`data: ${JSON.stringify(event)}\n\n`);
      res.end("data: [DONE]\n\n");
    });
  });
  const file = fixture(t, base);
  const first = createXaiPromptSession({ envFile: file, requestedModel: "unexpected-model" });
  fs.writeFileSync(file, `XAI_API_KEY=SECOND_SECRET\nSAND_XAI_BASE_URL=${base}\nSAND_XAI_MODEL=second-model\n`);
  const second = createXaiPromptSession({ envFile: file });
  const [a, b] = await Promise.all([result(first, [{ name: "lookup", parameters: { type: "object" } }]), result(second)]);
  assert.equal(first.getModelId(), "test-model");
  assert.equal(second.getModelId(), "second-model");
  assert.deepEqual(new Set(requests.map(r => `${r.body.model}:${r.auth}`)), new Set(["test-model:Bearer TEST_SECRET", "second-model:Bearer SECOND_SECRET"]));
  assert.equal(a.parts.find(p => p.type === "text-delta").textDelta, "hello");
  assert.deepEqual(a.parts.find(p => p.type === "tool-call").args, { q: "ok" });
  assert.equal(a.response.finishReason, "tool-calls");
  assert.equal(a.usage.totalTokens, 5);
  assert.ok(Array.isArray(b.state));
  fs.writeFileSync(file, `SAND_XAI_BASE_URL=${base}\nSAND_XAI_MODEL=second-model\n`);
  assert.throws(() => createXaiPromptSession({ envFile: file }), /XAI_API_KEY/);
});

test("missing key never reads environment or falls back to Grok auth", t => {
  const file = fixture(t, "http://127.0.0.1:1/v1");
  fs.writeFileSync(file, "SAND_XAI_BASE_URL=http://127.0.0.1:1/v1\nSAND_XAI_MODEL=test\n");
  const old = process.env.XAI_API_KEY;
  process.env.XAI_API_KEY = "MUST_NOT_USE";
  try { assert.throws(() => createXaiPromptSession({ envFile: file }), /XAI_API_KEY/); }
  finally { if (old === undefined) delete process.env.XAI_API_KEY; else process.env.XAI_API_KEY = old; }
  assert.throws(() => createXaiPromptSession({}), /absolute envFile/);
});

test("endpoint and configuration validation reject unsafe inputs", t => {
  for (const base of ["http://example.com/v1", "https://user:secret@example.com/v1", "https://example.com/v1?key=secret", "https://example.com/#secret", "file:///tmp/test"]) {
    assert.throws(() => createXaiPromptSession({ envFile: fixture(t, base) }), /endpoint/);
  }
  assert.throws(() => createXaiPromptSession({ envFile: fixture(t, "https://example.com/v1", "NODE_OPTIONS=bad\n") }), /unsupported key/);
  assert.throws(() => createXaiPromptSession({ envFile: fixture(t, "https://example.com/v1", "XAI_API_KEY=duplicate\n") }), /duplicate key/);
});

test("HTTP errors and redirects never expose body or forward credentials", async t => {
  let redirected = 0;
  const destination = await server(t, (req, res) => { redirected++; res.end(); });
  const base = await server(t, (req, res) => { res.writeHead(302, { Location: destination }); res.end("TEST_SECRET private prompt"); });
  const logs = [];
  const original = console.error;
  console.error = (...args) => logs.push(args.join(" "));
  let output;
  try { output = await result(createXaiPromptSession({ envFile: fixture(t, base + "/private-path") })); }
  finally { console.error = original; }
  assert.equal(redirected, 0);
  assert.equal(output.response.finishReason, "error");
  assert.equal(output.parts.find(p => p.type === "error").error.message, "ungrok provider HTTP 302");
  assert.doesNotMatch(logs.join("\n"), /TEST_SECRET|private prompt|private-path/);
});

test("schema normalization remains compatible", () => {
  assert.deepEqual(normalizeToolParameters(null), { type: "object", properties: {} });
  assert.deepEqual(normalizeToolParameters({ jsonSchema: { type: "object" } }), { type: "object", properties: {} });
});

test("unsafe file permissions, symlinks and oversized configuration are rejected", t => {
  const file = fixture(t, "https://example.com/v1");
  fs.chmodSync(file, 0o644);
  assert.throws(() => createXaiPromptSession({ envFile: file }), /mode-600/);
  fs.chmodSync(file, 0o600);
  const link = file + ".link";
  fs.symlinkSync(file, link);
  assert.throws(() => createXaiPromptSession({ envFile: link }), /regular file/);
  fs.appendFileSync(file, "#".repeat(65536));
  assert.throws(() => createXaiPromptSession({ envFile: file }), /64 KiB/);
});

test("oversized SSE and non-SSE success responses fail safely", async t => {
  for (const body of ["data: " + "x".repeat(1024 * 1024 + 1), '{"message":"secret response"}']) {
    const base = await server(t, (req, res) => { res.writeHead(200); res.end(body); });
    const output = await result(createXaiPromptSession({ envFile: fixture(t, base) }));
    assert.equal(output.response.finishReason, "error");
    assert.equal(output.parts.find(p => p.type === "error").error.message, "ungrok provider request failed");
  }
});
