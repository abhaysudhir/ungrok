#!/usr/bin/env node
"use strict";
// Opt-in integration check. Uses synthetic data and subscription quota only.
// Does not install a host patch, execute Grok tools, or alter native sign-in.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const zlib = require("node:zlib");
const crypto = require("node:crypto");
const { createXaiPromptSession } = require("../vendor/xai-prompt-session.cjs");

function options(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    const key = argv[i];
    if (key === "--yes") opts.yes = true;
    else if (["--provider", "--cli", "--model"].includes(key) && argv[i + 1] && !argv[i + 1].startsWith("--")) {
      if (opts[key.slice(2)] !== undefined) throw new Error("Duplicate option.");
      opts[key.slice(2)] = argv[++i];
    } else throw new Error("Usage: node scripts/verify_subscription.cjs --provider claude|chatgpt --cli /absolute/client [--model MODEL] --yes");
  }
  if (!opts.yes) throw new Error("This check makes synthetic model requests using your subscription quota. Add --yes to run.");
  if (!["claude", "chatgpt"].includes(opts.provider) || !opts.cli || !path.isAbsolute(opts.cli)) throw new Error("Choose a provider and an absolute official client path.");
  if (Object.values(opts).some(value => typeof value === "string" && /[\x00-\x1f\x7f]/.test(value))) throw new Error("Invalid option value.");
  return opts;
}

function solidPng(rgb) {
  function chunk(type, data) {
    const body = Buffer.concat([Buffer.from(type), data]);
    let crc = 0xffffffff;
    for (const byte of body) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit++) crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
    const length = Buffer.alloc(4), check = Buffer.alloc(4);
    length.writeUInt32BE(data.length); check.writeUInt32BE((crc ^ 0xffffffff) >>> 0);
    return Buffer.concat([length, body, check]);
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(64, 0); header.writeUInt32BE(64, 4); header[8] = 8; header[9] = 2;
  const rows = [];
  for (let y = 0; y < 64; y++) rows.push(Buffer.from([0]), Buffer.from(Array.from({ length: 64 }, () => rgb).flat()));
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk("IHDR", header), chunk("IDAT", zlib.deflateSync(Buffer.concat(rows))), chunk("IEND", Buffer.alloc(0))]);
}

async function step(executor, tools = []) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  const stream = executor.stream({ signal: controller.signal }, crypto.randomUUID(), tools);
  try {
    const parts = [];
    for await (const part of stream.fullStream) parts.push(part);
    const response = await stream.response;
    assert.notEqual(response.finishReason, "error", "Native adapter step failed. Run ungrok probe for readiness diagnostics.");
    return { response, parts, text: parts.filter(part => part.type === "text-delta").map(part => part.textDelta).join("").trim() };
  } finally { clearTimeout(timer); }
}

async function verify(opts) {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "ungrok-verify-"));
  fs.chmodSync(scratch, 0o700);
  try {
    const config = path.join(scratch, "subscription.env");
    fs.writeFileSync(config, `UNGROK_PROVIDER=${opts.provider}\nUNGROK_CLI=${opts.cli}\n${opts.model ? `UNGROK_MODEL=${opts.model}\n` : ""}`, { mode: 0o600 });
    const session = createXaiPromptSession({ envFile: config });
    const text = await step(session.getExecutor([{ role: "user", content: "Reply exactly UNGROK_TEXT_OK. Do not call tools." }]));
    assert.equal(text.text, "UNGROK_TEXT_OK");
    console.log("PASS native subscription text");

    const tools = [{ name: "ungrok_echo", description: "A synthetic host tool used only by this verification script.", parameters: {
      type: "object", properties: { value: { type: "string" } }, required: ["value"], additionalProperties: false,
    } }];
    const executor = session.getExecutor([{ role: "user", content: "Call ungrok_echo exactly once with value bridge-check. Wait for its result before answering." }]);
    const proposed = await step(executor, tools);
    const calls = proposed.parts.filter(part => part.type === "tool-call");
    assert.equal(calls.length, 1); assert.equal(calls[0].toolName, "ungrok_echo");
    assert.deepEqual(calls[0].args, { value: "bridge-check" });
    console.log("PASS host tool proposal, no real tool executed");
    const sentinel = "UNGROK_RESULT_" + crypto.randomBytes(6).toString("hex");
    executor.appendMessages(proposed.response.messages);
    executor.appendMessages([{ role: "tool", tool_call_id: calls[0].toolCallId, content: sentinel },
      { role: "user", content: "Reply with only the exact tool result you just received. Do not call any more tools." }]);
    const followed = await step(executor, tools);
    assert.equal(followed.text, sentinel);
    assert.equal(followed.parts.filter(part => part.type === "tool-call").length, 0);
    console.log("PASS tool-result follow-up");

    const image = rgb => ({ type: "image", mimeType: "image/png", data: solidPng(rgb) });
    const vision = session.getExecutor([{ role: "user", content: "Inspect both attached images. Reply with just their two dominant colors, in attachment order, separated by a space." },
      { role: "user", content: [image([255,0,0]), image([0,0,255])] }]);
    const seen = await step(vision);
    assert.equal(seen.text.toLowerCase().replace(/[.,]/g, ""), "red blue");
    console.log("PASS adjacent message plus two binary images");
    vision.appendMessages(seen.response.messages);
    vision.appendMessages([{ role: "user", content: "What was the color of the second image? Reply with just that color." }]);
    const remembered = await step(vision);
    assert.equal(remembered.text.toLowerCase().replace(/[.,]/g, ""), "blue");
    console.log("PASS image follow-up");
    console.log(`Verified ${opts.provider}: 5 synthetic native adapter checks. This is not a live Grok Bot host test.`);
  } finally { fs.rmSync(scratch, { recursive: true, force: true }); }
}

if (require.main === module) {
  Promise.resolve().then(() => verify(options(process.argv.slice(2)))).catch(error => {
    console.error("Verification failed: " + error.message); process.exitCode = 1;
  });
}
module.exports = { solidPng, options };
