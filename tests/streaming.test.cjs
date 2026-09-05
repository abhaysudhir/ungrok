"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
process.env.SAND_XAI_DEBUG_LOG = "/dev/null";
const { createXaiPromptSession } = require(process.env.UNGROK_TEST_ADAPTER || "../vendor/xai-prompt-session.cjs");
async function bounded(promise) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("stream did not settle")), 1000); })]); }
  finally { clearTimeout(timer); }
}
async function fixture(t, handler) {
  const server = http.createServer(handler);
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => { server.closeAllConnections(); server.close(); });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "ungrok-stream-test-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const envFile = path.join(dir, "config.env");
  fs.writeFileSync(envFile, `XAI_API_KEY=mock-key\nSAND_XAI_MODEL=mock-model\nSAND_XAI_BASE_URL=http://127.0.0.1:${server.address().port}/v1\n`, { mode: 0o600 });
  const old = process.env.SAND_XAI_ENV_FILE;
  process.env.SAND_XAI_ENV_FILE = envFile;
  t.after(() => { if (old === undefined) delete process.env.SAND_XAI_ENV_FILE; else process.env.SAND_XAI_ENV_FILE = old; });
  return createXaiPromptSession({ envFile }).getExecutor([{ role: "user", content: "first" }]);
}
async function allMetadata(stream) {
  return Promise.all([stream.response, stream.usage, stream.extendedUsage, stream.providerMetadata, stream.invocationId]);
}
test("first delta arrives before HTTP end; iterator return cancels pending next and upstream", async t => {
  let closed;
  const socketClosed = new Promise(resolve => { closed = resolve; });
  const ex = await fixture(t, (req, res) => {
    req.resume();
    req.on("end", () => {
      res.on("close", closed);
      res.writeHead(200, { "content-type": "text/event-stream" });
      res.write('data: {"choices":[{"delta":{"content":"early"}}]}\n\n');
    });
  });
  const stream = ex.stream({}, "id", []);
  assert.equal((await bounded(stream.fullStream.next())).value.textDelta, "early");
  const waiting = stream.fullStream.next();
  assert.equal((await bounded(stream.fullStream.return())).done, true);
  assert.equal((await bounded(waiting)).done, true);
  await bounded(socketClosed);
  assert.equal((await bounded(allMetadata(stream)))[0].finishReason, "error");
});
test("caller abort stops request; later appended message can run separately", async t => {
  let count = 0;
  const ex = await fixture(t, (req, res) => {
    let raw = "";
    req.on("data", c => { raw += c; });
    req.on("end", () => {
      count++;
      res.writeHead(200, { "content-type": "text/event-stream" });
      if (count === 1) res.write('data: {"choices":[{"delta":{"content":"first"}}]}\n\n');
      else {
        assert.match(JSON.stringify(JSON.parse(raw).messages), /second/);
        res.end('data: {"choices":[{"delta":{"content":"second reply"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n');
      }
    });
  });
  const controller = new AbortController();
  const first = ex.stream({ abortSignal: controller.signal }, "first", []);
  await bounded(first.fullStream.next());
  controller.abort();
  assert.equal((await bounded(allMetadata(first)))[0].finishReason, "error");
  ex.appendMessages([{ role: "user", content: "second" }]);
  const second = ex.stream({}, "second", []);
  assert.equal((await bounded(second.fullStream.next())).value.textDelta, "second reply");
  assert.equal((await bounded(allMetadata(second)))[0].finishReason, "stop");
});
test("abrupt provider disconnect settles promises instead of hanging", async t => {
  const ex = await fixture(t, (req, res) => {
    req.resume(); req.on("end", () => { res.writeHead(200); res.flushHeaders(); setImmediate(() => res.destroy()); });
  });
  const stream = ex.stream({}, "id", []);
  assert.equal((await bounded(allMetadata(stream)))[0].finishReason, "error");
  const parts = [];
  for await (const part of stream.fullStream) parts.push(part);
  assert.ok(parts.some(part => part.type === "error"));
});
test("pre-request conversion exception becomes error result, never detached rejection", async t => {
  const ex = await fixture(t, (req, res) => { res.end(); });
  const tools = [{ get name() { throw new Error("private conversion error"); } }];
  const stream = ex.stream({}, "id", tools);
  const parts = [];
  for await (const part of stream.fullStream) parts.push(part);
  assert.equal(parts.find(p => p.type === "error").error.message, "provider request preparation failed");
  assert.equal((await bounded(allMetadata(stream)))[0].finishReason, "error");
});
