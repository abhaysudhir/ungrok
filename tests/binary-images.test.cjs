"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { convertMessages } = require(process.env.UNGROK_TEST_ADAPTER || "../vendor/xai-prompt-session.cjs");
const png = Buffer.from([137,80,78,71,13,10,26,10,1,2,3]);
function urls(image, fields = {}) {
  return convertMessages([{ role: "user", content: [{ type: "image", image, ...fields }] }])
    .flatMap(m => Array.isArray(m.content) ? m.content : []).filter(p => p.type === "image_url").map(p => p.image_url.url);
}
test("Buffer Uint8Array ArrayBuffer and offset views preserve exact image bytes", () => {
  const padded = Buffer.concat([Buffer.from([0,0]), png, Buffer.from([0])]);
  for (const bytes of [png, new Uint8Array(png), Uint8Array.from(png).buffer, new DataView(padded.buffer, padded.byteOffset + 2, png.length)]) {
    assert.deepEqual(urls(bytes, { mediaType: "image/png" }), [`data:image/png;base64,${png.toString("base64")}`]);
  }
});
test("binary images sniff JPEG GIF WebP without assuming PNG", () => {
  for (const [bytes, mime] of [[Buffer.from([255,216,255,1]), "image/jpeg"], [Buffer.from("GIF89a123"), "image/gif"], [Buffer.from("RIFF1234WEBP"), "image/webp"]]) {
    assert.deepEqual(urls(bytes), [`data:${mime};base64,${bytes.toString("base64")}`]);
  }
});
test("unknown and MIME-mismatched binary images are not sent as invalid URLs", () => {
  assert.deepEqual(urls(png, { mimeType: "image/jpeg" }), []);
  assert.deepEqual(urls(Buffer.from("not an image")), []);
});
test("URL instances survive message-wide unwrap", () => {
  assert.deepEqual(urls(new URL("https://example.com/image.png")), ["https://example.com/image.png"]);
});
test("one MiB typed image encodes near base64 size, never numeric property JSON", () => {
  const bytes = new Uint8Array(1024 * 1024);
  bytes.set(png);
  const output = urls(bytes)[0];
  assert.ok(output.length < 1.34 * bytes.length + 100);
  assert.deepEqual(Buffer.from(output.split(",")[1], "base64"), Buffer.from(bytes));
});
test("reused typed image objects are preserved in multiple content parts", () => {
  const bytes = new Uint8Array(png);
  const converted = convertMessages([{ role: "user", content: [{ type: "image", image: bytes }, { type: "image", image: bytes }] }]);
  assert.equal(converted[0].content.filter(p => p.type === "image_url").length, 2);
});
test("binary image byte cap prevents oversized encoding", () => {
  const old = console.error;
  console.error = () => {};
  try {
    const bytes = new Uint8Array(20 * 1024 * 1024 + 1); bytes.set(png);
    assert.deepEqual(urls(bytes), []);
  } finally { console.error = old; }
});
