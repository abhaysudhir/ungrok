"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const zlib = require("node:zlib");
const { options, solidPng } = require("../scripts/verify_subscription.cjs");

test("live verification requires explicit consent and never accepts a credential flag", () => {
  assert.throws(() => options(["--provider", "claude", "--cli", "/client"]), /quota/);
  assert.throws(() => options(["--provider", "claude", "--cli", "/client", "--api-key", "secret", "--yes"]), /Usage/);
  assert.throws(() => options(["--provider", "other", "--cli", "/client", "--yes"]), /provider/);
  assert.throws(() => options(["--provider", "claude", "--cli", "client", "--yes"]), /absolute/);
  assert.throws(() => options(["--provider", "claude", "--cli", "/client\nBAD=1", "--yes"]), /Invalid/);
  assert.deepEqual(options(["--provider", "chatgpt", "--cli", "/client", "--model", "model", "--yes"]), {
    provider: "chatgpt", cli: "/client", model: "model", yes: true,
  });
});

test("synthetic image fixtures really contain the expected pixels", () => {
  for (const rgb of [[255, 0, 0], [0, 0, 255]]) {
    const png = solidPng(rgb);
    assert.deepEqual([...png.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
    assert.equal(png.readUInt32BE(16), 64);
    assert.equal(png.readUInt32BE(20), 64);
    let offset = 8, compressed;
    while (offset < png.length) {
      const size = png.readUInt32BE(offset);
      if (png.toString("ascii", offset + 4, offset + 8) === "IDAT") compressed = png.subarray(offset + 8, offset + 8 + size);
      offset += 12 + size;
    }
    const raw = zlib.inflateSync(compressed);
    assert.equal(raw.length, 64 * 193);
    for (let row = 0; row < 64; row++) {
      assert.equal(raw[row * 193], 0);
      for (let x = 0; x < 64; x++) assert.deepEqual([...raw.subarray(row * 193 + 1 + x * 3, row * 193 + 4 + x * 3)], rgb);
    }
  }
});
