"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { convertMessages, trimConvertedMessages } = require(process.env.UNGROK_TEST_ADAPTER || "../vendor/xai-prompt-session.cjs");
function image(id) { return { type: "image_url", image_url: { url: `data:image/jpeg;base64,${"A".repeat(500000)}${id}` } }; }
function imageCount(messages) { return messages.flatMap(m => Array.isArray(m.content) ? m.content : []).filter(p => p.type === "image_url").length; }
function oldHistory() {
  return Array.from({ length: 80 }, (_, i) => [{ role: "user", content: `old${i}:` + "x".repeat(16000) }, { role: "assistant", content: "y".repeat(16000) }]).flat();
}
function request() { return { role: "user", content: [{ type: "text", text: "WRITE_MY_DOCUMENT_FROM_ALL_FOUR_PAGES" }, ...Array.from({ length: 4 }, (_, i) => image(i))] }; }
function containsRequest(messages) { return messages.some(m => m.role === "user" && JSON.stringify(m.content).includes("WRITE_MY_DOCUMENT_FROM_ALL_FOUR_PAGES")); }
test("latest four-image request survives subsequent assistant and synthetic continuation", () => {
  const raw = [...oldHistory(), request(), { role: "assistant", content: "Got all four pages; reading them into your document." }];
  const trimmed = trimConvertedMessages(convertMessages(raw), "test-model");
  assert.ok(containsRequest(trimmed));
  assert.equal(imageCount(trimmed), 4);
  assert.ok(trimmed.length < raw.length);
  assert.ok(trimmed.some(m => m.content === "Got all four pages; reading them into your document."));
  assert.ok(trimmed.every(m => !Object.keys(m).some(k => /synthetic/i.test(k))));
});
test("latest image request survives a tool-call/result follow-up under long-history pressure", () => {
  const call = { role: "assistant", content: [{ type: "tool-call", toolCallId: "read1", toolName: "read", args: {} }] };
  const tool = { role: "tool", tool_call_id: "read1", content: "z".repeat(50000) };
  const trimmed = trimConvertedMessages(convertMessages([...oldHistory(), request(), call, tool]), "test-model");
  assert.ok(containsRequest(trimmed));
  assert.equal(imageCount(trimmed), 4);
  assert.ok(trimmed.some(m => m.tool_calls?.some(t => t.id === "read1")));
  assert.ok(trimmed.some(m => m.role === "tool" && m.tool_call_id === "read1"));
});
test("ten current images across four-plus-six upload batches remain available", () => {
  const raw = [request(), { role: "assistant", content: "Received first four." },
    { role: "user", content: [{ type: "text", text: "Here are the remaining six; use all ten." }, ...Array.from({ length: 6 }, (_, i) => image(i + 4))] },
    { role: "assistant", content: "Starting document." }];
  assert.equal(imageCount(trimConvertedMessages(convertMessages(raw), "test-model")), 10);
});
test("history image retention is bounded without truncating bytes or newest request", () => {
  const raw = Array.from({ length: 25 }, (_, i) => [{ role: "user", content: [image(i)] }, { role: "assistant", content: `ack ${i}` }]).flat();
  const trimmed = trimConvertedMessages(convertMessages(raw), "test-model");
  assert.equal(imageCount(trimmed), 20);
  assert.match(JSON.stringify(trimmed), /Earlier image omitted/);
  assert.ok(trimmed.some(m => Array.isArray(m.content) && m.content.some(p => p.image_url?.url.endsWith("24"))));
});
test("too many images in newest request fails rather than silently sending a partial request", () => {
  assert.throws(() => trimConvertedMessages(convertMessages([{ role: "user", content: Array.from({ length: 21 }, (_, i) => image(i)) }]), "test-model"), /20 image/);
});
