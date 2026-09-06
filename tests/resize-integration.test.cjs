const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const adapterSource = path.join(__dirname, '../vendor/xai-prompt-session.cjs');
const helperSource = path.join(__dirname, '../scripts/resize_image.py');
function isolated(t, helper) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ungrok-resize-test-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const moduleFile = path.join(dir, 'adapter.cjs');
  fs.copyFileSync(adapterSource, moduleFile);
  fs.copyFileSync(path.join(__dirname, '../vendor/subscription-runtime.cjs'), path.join(dir, 'subscription-runtime.cjs'));
  if (helper === true) fs.copyFileSync(helperSource, path.join(dir, 'ungrok-resize-image.py'));
  else if (typeof helper === 'string') fs.writeFileSync(path.join(dir, 'ungrok-resize-image.py'), helper);
  return require(moduleFile).prepareInlineImages;
}
const imageMessage = (url) => [{ role: 'user', content: [{ type: 'image_url', image_url: { url, detail: 'high' } }] }];
const largeDataUrl = 'data:image/png;base64,' + 'A'.repeat(200004);

test('small inline and remote images pass through without a helper or fetching', async (t) => {
  const prepare = isolated(t, false);
  const messages = imageMessage('https://invalid.example/never-fetch.png');
  messages[0].content.push({ type: 'image_url', image_url: { url: 'data:image/png;base64,AAAA' } });
  const result = await prepare(messages);
  assert.deepEqual(result, messages);
  assert.notEqual(result, messages);
  assert.notEqual(result[0].content, messages[0].content);
});

test('large inline image fails closed when helper is missing', async (t) => {
  await assert.rejects(isolated(t, false)(imageMessage(largeDataUrl)), /requires the resize helper/);
});

test('oversized input is rejected before starting a helper', async (t) => {
  const tooLarge = 'data:image/png;base64,' + 'A'.repeat(Math.ceil(20 * 1024 * 1024 / 3) * 4 + 4);
  await assert.rejects(isolated(t, false)(imageMessage(tooLarge)), /20 MiB input limit/);
});

test('helper output is validated and contents are not exposed by errors', async (t) => {
  const prepare = isolated(t, 'import sys\nsys.stdin.read()\nprint("SECRET_BAD_IMAGE")\n');
  await assert.rejects(prepare(imageMessage(largeDataUrl)), (error) => {
    assert.match(error.message, /image resize failed/);
    assert.ok(!error.message.includes('SECRET_BAD_IMAGE'));
    return true;
  });
});

test('helper stdout is capped', async (t) => {
  const prepare = isolated(t, 'import sys\nsys.stdin.read()\nsys.stdout.write("A" * (6 * 1024 * 1024 + 1))\n');
  await assert.rejects(prepare(imageMessage(largeDataUrl)), /output exceeds limit/);
});

test('cancel aborts an active resize without waiting for helper completion', async (t) => {
  const prepare = isolated(t, 'import sys,time\nsys.stdin.read()\ntime.sleep(30)\n');
  const controller = new AbortController();
  const promise = prepare(imageMessage(largeDataUrl), controller.signal);
  const timer = setTimeout(() => controller.abort(), 50);
  t.after(() => clearTimeout(timer));
  await assert.rejects(promise, /provider request cancelled/);
});

test('multiple large images are processed sequentially and keep their order', async (t) => {
  const childProcess = require('node:child_process');
  const realSpawn = childProcess.spawn;
  let active = 0;
  let maximum = 0;
  let calls = 0;
  childProcess.spawn = (...args) => {
    calls++;
    active++;
    maximum = Math.max(maximum, active);
    const child = realSpawn(...args);
    child.once('close', () => active--);
    return child;
  };
  t.after(() => { childProcess.spawn = realSpawn; });
  const prepare = isolated(t, 'import sys,json,time\nsys.stdin.read()\ntime.sleep(0.02)\nprint(json.dumps({"mimeType":"image/jpeg","data":"AAAA"}))\n');
  const messages = imageMessage(largeDataUrl);
  messages[0].content.push({ type: 'text', text: 'between images' });
  messages[0].content.push({ type: 'image_url', image_url: { url: largeDataUrl } });
  const result = await prepare(messages);
  assert.equal(calls, 2);
  assert.equal(maximum, 1);
  assert.equal(result[0].content[1].text, 'between images');
  assert.equal(result[0].content[0].image_url.url, 'data:image/jpeg;base64,AAAA');
  assert.equal(result[0].content[2].image_url.url, 'data:image/jpeg;base64,AAAA');
});

test('Pillow downsamples an inline request copy and preserves original objects', async (t) => {
  const fixture = spawnSync('python3', ['-c',
    'from PIL import Image\nimport os,io,base64\nim=Image.frombytes("RGB", (1800,400), os.urandom(1800*400*3))\nb=io.BytesIO()\nim.save(b,format="PNG")\nprint(base64.b64encode(b.getvalue()).decode())'],
    { encoding: 'utf8', maxBuffer: 12 * 1024 * 1024 });
  assert.equal(fixture.status, 0, 'Python Pillow is required for image integration tests');
  const url = 'data:image/png;base64,' + fixture.stdout.trim();
  assert.ok(url.length > 200000);
  const messages = imageMessage(url);
  Object.freeze(messages[0].content[0].image_url);
  Object.freeze(messages[0].content[0]);
  Object.freeze(messages[0].content);
  Object.freeze(messages[0]);
  Object.freeze(messages);
  const result = await isolated(t, true)(messages);
  const resized = result[0].content[0].image_url.url;
  assert.match(resized, /^data:image\/jpeg;base64,/);
  assert.ok(resized.length < url.length);
  assert.equal(result[0].content[0].image_url.detail, 'high');
  assert.equal(messages[0].content[0].image_url.url, url);
  const dimensions = spawnSync('python3', ['-c',
    'from PIL import Image\nimport sys,io,base64\nim=Image.open(io.BytesIO(base64.b64decode(sys.stdin.read())))\nprint(max(im.size))'],
    { input: resized.split(',')[1], encoding: 'utf8' });
  assert.equal(dimensions.status, 0);
  assert.ok(Number(dimensions.stdout.trim()) <= 1568);
});
