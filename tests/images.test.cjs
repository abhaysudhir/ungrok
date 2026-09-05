"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const adapter = require(process.env.UNGROK_TEST_ADAPTER || "../vendor/xai-prompt-session.cjs");

const image = (id, size = 4) => ({ type: "image_url", image_url: {
  url: "data:image/png;base64," + String.fromCharCode(65 + id).repeat(size),
} });
const convert = (messages) => adapter.trimConvertedMessages(adapter.convertMessages(messages), "claude-opus-5");
const parts = (messages) => messages.flatMap((m) => Array.isArray(m.content) ? m.content : []);
const imageUrls = (messages) => parts(messages).filter((p) => p.type === "image_url").map((p) => p.image_url.url);

test("adjacent user text and four images retain images and both text messages", () => {
  const images = Array.from({ length: 4 }, (_, i) => image(i));
  const result = convert([
    { role: "user", content: "first instruction" },
    { role: "user", content: [{ type: "text", text: "second instruction" }, ...images] },
  ]);
  assert.equal(result.length, 1);
  assert.deepEqual(imageUrls(result), images.map((p) => p.image_url.url));
  assert.deepEqual(parts(result).filter((p) => p.type === "text").map((p) => p.text),
    ["first instruction", "second instruction"]);
});

test("array-array-string merges preserve ordered content without duplicating images", () => {
  const result = convert([
    { role: "user", content: [image(0)] },
    { role: "user", content: [{ type: "text", text: "middle" }, image(1)] },
    { role: "user", content: "last" },
  ]);
  assert.deepEqual(parts(result).map((p) => p.type), ["image_url", "text", "image_url", "text"]);
  assert.deepEqual(imageUrls(result), [image(0).image_url.url, image(1).image_url.url]);
  assert.equal(parts(result).at(-1).text, "last");
});

test("plain text merging keeps existing separators", () => {
  assert.deepEqual(convert([{ role: "user", content: "one" }, { role: "user", content: "two" }]),
    [{ role: "user", content: "one\n\ntwo" }]);
});

test("large image URLs are not silently truncated or discarded", () => {
  const images = Array.from({ length: 4 }, (_, i) => image(i, 200000));
  const result = convert([{ role: "user", content: "inspect" }, { role: "user", content: images }]);
  assert.deepEqual(imageUrls(result), images.map((p) => p.image_url.url));
});

test("supported image URL and base64 source shapes normalize to image_url", () => {
  const result = adapter.convertMessages([{ role: "user", content: [
    { type: "image", source: { type: "base64", media_type: "image/png", data: "AQID" } },
    { type: "image", mimeType: "image/jpeg", data: "BAUG" },
    { type: "image", source: { type: "url", url: "https://example.invalid/image.webp" } },
    { type: "input_image", image_url: "https://example.invalid/image.png" },
  ] }]);
  assert.deepEqual(imageUrls(result), ["data:image/png;base64,AQID", "data:image/jpeg;base64,BAUG",
    "https://example.invalid/image.webp", "https://example.invalid/image.png"]);
});

test("invalid MIME or base64 does not become a malformed image URL", () => {
  const result = adapter.convertMessages([{ role: "user", content: [
    { type: "text", text: "keep this" },
    { type: "image", source: { type: "base64", media_type: "text/html", data: "AQID" } },
    { type: "image", source: { type: "base64", media_type: "image/png", data: "not base64!" } },
    { type: "image", source: { type: "base64", media_type: "image/png", data: "AQID==" } },
    { type: "image", image: { unexpected: "object" } },
  ] }]);
  assert.deepEqual(imageUrls(result), []);
  assert.equal(result[0].content, "keep this");
});
