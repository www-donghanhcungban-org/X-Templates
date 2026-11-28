import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { createServer } from 'node:http';
import { copyFile, mkdtemp, rm, symlink, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const template = fileURLToPath(new URL('../framework/templates/ui-gates/verify-render.mjs', import.meta.url));
const nodeModules = fileURLToPath(new URL('./verify-render-deps/node_modules', import.meta.url));
const SAMPLE_IMAGE = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
const STATES = ['default', 'hover', 'focus'];

function page({ css = '', narrowCSS = '', markup = '' } = {}) {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Verify-render sample</title>
<style>
  body { margin: 24px; background: #fff; color: #111; }
  button { min-width: 48px; min-height: 44px; background: #fff; color: #111; border: 2px solid currentColor; }
  button:hover, button:focus-visible { background: #111; color: #fff; }
  button:focus-visible { outline: 3px solid #00e; outline-offset: 2px; }
  @media (prefers-color-scheme: dark) {
    body { background: #111; color: #fff; }
    button:focus-visible { outline-color: #9cf; }
  }
  .narrow { display: none; }
  @media (max-width: 320px) { ${narrowCSS} }
  ${css}
</style>
</head>
<body><main><h1>Book a room</h1><button id="sample">Check rooms</button>${markup}</main></body>
</html>`;
}

async function fixture(t, html) {
  const root = await mkdtemp(join(tmpdir(), 'xt-verify-render-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const script = join(root, 'verify-render.mjs');
  const sample = 'sample #1.html';
  await copyFile(template, script);
  await symlink(nodeModules, join(root, 'node_modules'), 'junction');
  await writeFile(join(root, sample), html);
  const target = pathToFileURL(join(root, sample)).href;
  return {
    target,
    async exceptions(entries) {
      const file = join(root, 'exceptions.json');
      await writeFile(file, JSON.stringify({ schema: 1, exceptions: entries }));
      return file;
    },
    async run(args = [], env = process.env, targets = [sample]) {
      let result;
      try {
        const { stdout, stderr } = await execute(process.execPath, [script, ...targets, ...args], { cwd: root, env });
        result = { code: 0, stdout, stderr };
      } catch (error) {
        if (typeof error.code !== 'number') throw error;
        result = { code: error.code, stdout: error.stdout, stderr: error.stderr };
      }
      // Cổng đã che userinfo/query khỏi định danh; số đo từng phạm vi vào log CI để xem lại khi job xanh.
      t.diagnostic(`verify-render exit=${result.code}\n${result.stdout.trimEnd()}`);
      return result;
    },
  };
}

async function serve(t, routes) {
  const server = createServer((request, response) => {
    const route = routes[new URL(request.url, 'http://localhost').pathname];
    response.writeHead(route ? 200 : 404, { 'content-type': 'text/html; charset=utf-8' });
    response.end(route ?? '<!doctype html><title>missing</title>');
  });
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  t.after(() => new Promise((done) => server.close(done)));
  return server.address().port;
}

const status = ({ code, stdout, stderr }, expected) => assert.equal(code, expected, stdout + stderr);
const scoped = (width, theme, state) => `viewport=${width}x800 theme=${theme} state=${state}`;
const count = (stdout, label, width, theme, state, expected) => {
  const line = stdout.split('\n').find((row) => row.startsWith(label + ' ') && row.includes(scoped(width, theme, state)));
  assert.ok(line, stdout);
  assert.ok(line.endsWith(expected), line);
};

function exception(target, overrides = {}) {
  return {
    target, width: 320, theme: 'light', state: 'default', check: 'contrast', element: '#sample',
    reason: 'Gradient requires a manual contrast reading', evidence: 'reviews/manual-contrast.md#sample',
    expires: '2099-12-31', ...overrides,
  };
}

test('strict axe and contrast actually run on desktop and both default narrow widths in each requested theme', async (t) => {
  const sample = await fixture(t, page());
  const result = await sample.run(['--strict', '--themes', 'light,dark']);
  status(result, 0);
  assert.doesNotMatch(result.stdout, /^UNMEASURED /m);
  assert.match(result.stdout, /sample%20%231\.html/);
  for (const width of [1280, 320, 280]) {
    for (const theme of ['light', 'dark']) {
      const axe = result.stdout.split('\n').find((line) => line.startsWith('AXE ') && line.includes(scoped(width, theme, 'default')));
      assert.match(axe ?? '', /measured=[1-9]\d* unmeasured=0 exempted=0$/);
      for (const state of STATES) count(result.stdout, 'CONTRAST', width, theme, state, 'measured=1 unmeasured=0 exempted=0');
    }
  }
});

test('axe fails for an image visible only at the narrow viewport, even with a matching exemption', async (t) => {
  const sample = await fixture(t, page({
    narrowCSS: '.narrow { display: inline-block; }',
    markup: `<img class="narrow" id="missing-alt" src="${SAMPLE_IMAGE}" width="32" height="32">`,
  }));
  const file = await sample.exceptions([
    exception(sample.target, { check: 'axe:image-alt', element: '#missing-alt' }),
  ]);
  const result = await sample.run(['--strict', '--widths', '320', '--exceptions', file]);
  status(result, 1);
  const failures = result.stdout.split('\n').filter((line) => line.startsWith('✗ '));
  assert.ok(failures.some((line) => line.includes(scoped(320, 'light', 'default')) && line.includes('check=axe:image-alt element="#missing-alt"')), result.stdout);
  assert.ok(!failures.some((line) => line.includes(scoped(1280, 'light', 'default'))), result.stdout);
  assert.match(result.stdout, /EXCEPTION UNUSED .*check=axe:image-alt/);
  assert.doesNotMatch(result.stdout, /^EXEMPTED .*check=axe:image-alt/m);
});

test('transparent hover inherits the Chromium canvas of the root color scheme', async (t) => {
  const sample = await fixture(t, page({ css: `
    :root { color-scheme: light dark; }
    body { background: transparent; }
    h1 { background: #fff; color: #111; }
    #sample:hover { background: transparent; color: #111; }
  ` }));
  const args = ['--strict', '--widths', '320'];
  const light = await sample.run([...args, '--themes', 'light']);
  status(light, 0);
  assert.doesNotMatch(light.stdout, /^(?:UNMEASURED|✗) /m);
  const dark = await sample.run([...args, '--themes', 'dark']);
  status(dark, 1);
  const failures = dark.stdout.split('\n').filter((line) => line.startsWith('✗ '));
  assert.equal(failures.length, 2, dark.stdout);
  for (const width of [1280, 320]) {
    assert.ok(failures.some((line) => line.includes(scoped(width, 'dark', 'hover')) &&
      line.includes('check=contrast element="#sample"')), dark.stdout);
    count(dark.stdout, 'CONTRAST', width, 'dark', 'hover', 'measured=1 unmeasured=0 exempted=0');
  }
});

test('strict fails on narrow gradient until every unmeasured rule and state is exempted', async (t) => {
  const sample = await fixture(t, page({
    narrowCSS: '#sample { background-image: linear-gradient(#ddd, #fff); color: #111; }',
  }));
  const args = ['--widths', '320'];
  const strict = await sample.run(['--strict', ...args]);
  status(strict, 1);
  for (const state of STATES) {
    count(strict.stdout, 'CONTRAST', 1280, 'light', state, 'measured=1 unmeasured=0 exempted=0');
    count(strict.stdout, 'CONTRAST', 320, 'light', state, 'measured=0 unmeasured=1 exempted=0');
  }
  assert.match(strict.stdout, /^UNMEASURED .*viewport=320x800 .*nền là ảnh\/gradient/m);
  const manualAxe = strict.stdout.split('\n').filter((line) => line.startsWith('UNMEASURED ') && line.includes('check=axe:'));
  const entries = STATES.map((state) => exception(sample.target, { state }));
  // axe may request manual review as well. Assert its exact expected scope before adding the independent review.
  for (const line of manualAxe) {
    assert.ok(line.includes(scoped(320, 'light', 'default')), line);
    assert.match(line, /check=axe:color-contrast element="#sample"/);
    entries.push(exception(sample.target, { check: 'axe:color-contrast' }));
  }
  const advisory = await sample.run(args);
  status(advisory, 0);
  assert.match(advisory.stdout, /^UNMEASURED /m);
  assert.doesNotMatch(advisory.stdout, /^✓/m);

  const file = await sample.exceptions(entries);
  const allowed = await sample.run(['--strict', ...args, '--exceptions', file]);
  status(allowed, 0);
  assert.match(allowed.stdout, /^UNMEASURED /m);
  assert.match(allowed.stdout, /^EXEMPTED .*reason=".+".* evidence=".+"/m);
  assert.doesNotMatch(allowed.stdout, /^✓/m);
  for (const state of STATES) count(allowed.stdout, 'CONTRAST', 320, 'light', state, 'measured=0 unmeasured=1 exempted=1');

  await sample.exceptions([
    ...entries.filter((item) => item.state !== 'focus'),
    exception(sample.target, { state: 'focus', expires: '2000-02-29' }),
    exception(sample.target, { state: 'focus', width: 1280 }),
  ]);
  const expired = await sample.run(['--strict', ...args, '--exceptions', file]);
  status(expired, 1);
  assert.match(expired.stdout, /EXCEPTION EXPIRED .*viewport=320x800 .*state=focus/);
  assert.match(expired.stdout, /EXCEPTION UNUSED .*viewport=1280x800 .*state=focus/);
});

test('malformed or conflicting exceptions and invalid widths fail before browser launch', async (t) => {
  const sample = await fixture(t, page());
  const invalid = [
    { expires: '2099-02-29' }, { expires: '2099-02-30' }, { evidence: ' ' }, { reason: '' },
    { width: 320.5 }, { check: 'layout' }, { element: '*' },
  ];
  for (const changes of invalid) {
    const file = await sample.exceptions([exception(sample.target, changes)]);
    const result = await sample.run(['--strict', '--exceptions', file]);
    status(result, 2);
    assert.match(result.stderr, /Cấu hình không hợp lệ/);
  }
  const duplicate = await sample.exceptions([exception(sample.target), exception(sample.target, { reason: 'Other' })]);
  const conflict = await sample.run(['--strict', '--exceptions', duplicate]);
  status(conflict, 2);
  assert.match(conflict.stderr, /trùng phạm vi/);
  const width = await sample.run(['--widths', '1.5,Infinity']);
  status(width, 2);
  assert.match(width.stderr, /số nguyên dương/);
});

test('disabled controls, including those inside a disabled fieldset, are outside the contrast scope', async (t) => {
  const sample = await fixture(t, page({
    markup: '<fieldset disabled><legend>Frozen</legend><button id="frozen" tabindex="0">Frozen</button></fieldset>' +
      '<button id="off" tabindex="0" disabled>Off</button>',
  }));
  const result = await sample.run(['--strict', '--widths', '320']);
  status(result, 0);
  assert.doesNotMatch(result.stdout, /^UNMEASURED /m);
  for (const state of STATES) count(result.stdout, 'CONTRAST', 320, 'light', state, 'measured=1 unmeasured=0 exempted=0');
});

test('report identifiers hide userinfo and query values while exceptions still match the full target', async (t) => {
  const port = await serve(t, { '/page.html': page() });
  const sample = await fixture(t, page());
  const target = `http://user:pw-secret@127.0.0.1:${port}/page.html?token=query-secret#frag-secret`;
  const result = await sample.run(['--strict', '--widths', '320'], process.env, [target]);
  status(result, 0);
  assert.doesNotMatch(result.stdout + result.stderr, /pw-secret|query-secret|frag-secret|user:/);
  assert.match(result.stdout, new RegExp(`^AXE target="http://127\\.0\\.0\\.1:${port}/page\\.html\\[đã che\\]" `, 'm'));
  const file = await sample.exceptions([exception(target, { check: 'axe:image-alt', element: '#missing' })]);
  const unused = await sample.run(['--strict', '--widths', '320', '--exceptions', file], process.env, [target]);
  status(unused, 0);
  assert.match(unused.stdout, /^EXCEPTION UNUSED target="http:\/\/127\.0\.0\.1:\d+\/page\.html\[đã che\]"/m);
  assert.doesNotMatch(unused.stdout + unused.stderr, /pw-secret|query-secret|frag-secret/);
});

test('an element identifier with an escaped asterisk is exact, while a bare or backslash-pair asterisk is a wildcard', async (t) => {
  const sample = await fixture(t, page({ markup: '<button id="star*name">Star</button>' }));
  const accepted = await sample.exceptions([exception(sample.target, { element: '#star\\*name' })]);
  const exact = await sample.run(['--strict', '--widths', '320', '--exceptions', accepted]);
  status(exact, 0);
  assert.match(exact.stdout, /EXCEPTION UNUSED .*element="#star\\\\\*name"/);
  for (const element of ['#star*name', '#a\\\\*']) {
    const file = await sample.exceptions([exception(sample.target, { element })]);
    const wildcard = await sample.run(['--strict', '--widths', '320', '--exceptions', file]);
    status(wildcard, 2);
    assert.match(wildcard.stderr, /ký tự đại diện/);
  }
});

test('an HTTP error page is UNMEASURED instead of passing', async (t) => {
  const port = await serve(t, { '/ok.html': page() });
  const sample = await fixture(t, page());
  const missing = `http://127.0.0.1:${port}/missing.html?token=query-secret`;
  const result = await sample.run(['--strict', '--widths', '320'], process.env, [missing]);
  status(result, 2);
  assert.match(result.stderr, /UNMEASURED.*HTTP 404 tại "?http:\/\/127\.0\.0\.1:\d+\/missing\.html\[đã che\]/);
  assert.doesNotMatch(result.stdout + result.stderr, /query-secret|^✓/m);
  const ok = await sample.run(['--strict', '--widths', '320'], process.env, [`http://127.0.0.1:${port}/ok.html`]);
  status(ok, 0);
});

async function closedPort() {
  const server = createServer();
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  const { port } = server.address();
  await new Promise((done) => server.close(done));
  return port;
}

test('a navigation failure does not echo userinfo, query or fragment of the target', async (t) => {
  const sample = await fixture(t, page());
  const target = `http://user:pw-secret@127.0.0.1:${await closedPort()}/p.html?token=query-secret#frag-secret`;
  const result = await sample.run(['--strict', '--widths', '320'], process.env, [target]);
  status(result, 2);
  assert.match(result.stderr, /UNMEASURED.*không chạy hết cổng/);
  assert.doesNotMatch(result.stdout + result.stderr, /pw-secret|query-secret|frag-secret/);
});

test('a hover colour reached through a transition is measured at its final value', async (t) => {
  const sample = await fixture(t, page({ css: `
    #sample { transition: color 2s linear; }
    #sample:hover, #sample:focus-visible { background: #fff; color: #d0d0d0; }
  ` }));
  const result = await sample.run(['--strict', '--widths', '320']);
  status(result, 1);
  const failures = result.stdout.split('\n').filter((line) => line.startsWith('✗ '));
  for (const width of [1280, 320]) {
    for (const state of ['hover', 'focus']) {
      assert.ok(failures.some((line) => line.includes(scoped(width, 'light', state)) &&
        line.includes('check=contrast element="#sample"')), result.stdout);
    }
  }
  assert.ok(!failures.some((line) => line.includes('state=default')), result.stdout);
});

test('an infinite animation on the control is UNMEASURED instead of a guess', async (t) => {
  // Keep both ends readable so axe does not fail based on when it samples the animation.
  const sample = await fixture(t, page({ css: `
    @keyframes pulse { from { color: #111; } to { color: #333; } }
    #sample { animation: pulse 1s infinite alternate; }
  ` }));
  const strict = await sample.run(['--strict', '--widths', '320']);
  status(strict, 1);
  assert.match(strict.stdout, /^UNMEASURED .*check=contrast element="#sample" — hoạt ảnh vô hạn/m);
  for (const state of STATES) count(strict.stdout, 'CONTRAST', 320, 'light', state, 'measured=0 unmeasured=1 exempted=0');
  const advisory = await sample.run(['--widths', '320']);
  status(advisory, 0);
  assert.doesNotMatch(advisory.stdout, /^✓/m);
});

const contrastLine = (stdout, needle) => stdout.split('\n').find((line) => line.startsWith('✗ ') && line.includes('check=contrast') && line.includes(needle));

test('controls inside an iframe are measured, not skipped', async (t) => {
  const inner = '<button style="color:#ddd;background:#fff;min-width:48px;min-height:44px">Pay</button>';
  const sample = await fixture(t, page({ markup: `<iframe title="payment" width="200" height="80" srcdoc="${inner.replaceAll('"', '&quot;')}"></iframe>` }));
  const result = await sample.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.ok(contrastLine(result.stdout, 'element="frame[1] '), result.stdout);
});

test('a control inside a shadow root is measured against the host background', async (t) => {
  const sample = await fixture(t, page({
    css: 'x-card { display: block; background: #111; padding: 8px; }',
    markup: `<x-card id="card"></x-card><script>
      const root = document.getElementById('card').attachShadow({ mode: 'open' });
      root.innerHTML = '<button style="color:#222;background:transparent;min-width:48px;min-height:44px">Shadow</button>';
    </script>`,
  }));
  const result = await sample.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.ok(contrastLine(result.stdout, 'state=default'), result.stdout);
});

test('text colour of a child element and of ::before is measured, not only the control colour', async (t) => {
  const child = await fixture(t, page({ markup: '<button id="child"><span style="color:#ddd">Quiet label</span></button>' }));
  const childResult = await child.run(['--strict', '--widths', '320']);
  status(childResult, 1);
  assert.ok(contrastLine(childResult.stdout, 'element="#child"'), childResult.stdout);
  const pseudo = await fixture(t, page({ css: '#icon::before { content: "!"; color: #ddd; }', markup: '<button id="icon">Alert</button>' }));
  const pseudoResult = await pseudo.run(['--strict', '--widths', '320']);
  status(pseudoResult, 1);
  assert.ok(contrastLine(pseudoResult.stdout, 'element="#icon"'), pseudoResult.stdout);
});

test('opacity and transparent text fill make a control UNMEASURED instead of a guess', async (t) => {
  const sample = await fixture(t, page({
    css: '#faded { opacity: .3; } #ghost { -webkit-text-fill-color: transparent; }',
    markup: '<button id="faded">Faded</button><button id="ghost">Ghost</button>',
  }));
  const result = await sample.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.match(result.stdout, /^UNMEASURED .*check=contrast element="#faded" — độ mờ/m);
  assert.match(result.stdout, /^UNMEASURED .*check=contrast element="#ghost" — chữ trong suốt/m);
});

const WIDE_TEXT = 'content that is far wider than its box and gets cut off';
const wideBox = (id, style) => `<div id="${id}" tabindex="0" role="region" aria-label="wide content" style="${style}"><div style="width:900px;white-space:nowrap">${WIDE_TEXT}</div></div>`;

test('bordered clipping uses the padding edge for fitting and cut text', async (t) => {
  for (const [id, overflow, direction, transform] of [
    ['ltr', 'hidden', 'ltr', ''], ['rtl', 'clip', 'rtl', ''],
    ['scaled', 'hidden', 'ltr', 'transform:scale(1.5);transform-origin:left top;'],
  ]) {
    const box = (text) => `<div id="${id}" dir="${direction}" style="overflow:${overflow};width:100px;border:20px solid;white-space:nowrap;font:20px/1 monospace;background:#fff;color:#111;${transform}">${text}</div>`;
    const fit = await fixture(t, page({ markup: box('12345678') }));
    status(await fit.run(['--strict', '--widths', '320']), 0);
    const cut = await fixture(t, page({ markup: box('123456789') }));
    const result = await cut.run(['--strict', '--widths', '320']);
    status(result, 1);
    assert.match(result.stdout, new RegExp(`check=reflow element="#${id}" — chữ bị cắt`));
  }
});

test('overflow clip margin extends the clipping edge but does not affect hidden', async (t) => {
  for (const [overflow, margin, expected] of [['clip', 0, 1], ['clip', 10, 0], ['hidden', 10, 1]]) {
    const sample = await fixture(t, page({ markup: `<p id="edge" style="width:100px;border:20px solid;white-space:nowrap;font:20px/1 monospace;overflow:${overflow};overflow-clip-margin:${margin}px">AVAILABLE</p>` }));
    const result = await sample.run(['--strict', '--widths', '320']);
    status(result, expected);
    if (expected) assert.match(result.stdout, /check=reflow element="#edge" — chữ bị cắt/);
    else assert.doesNotMatch(result.stdout, /check=reflow element="#edge"/);
  }
});

test('overflow clip geometry boxes without an explicit length use zero margin', async (t) => {
  const border = await fixture(t, page({ markup: `<p id="edge" style="width:100px;border:20px solid;white-space:nowrap;font:20px/1 monospace;overflow:clip;overflow-clip-margin:border-box">AVAILABLE</p>
    <script>if (!CSS.supports('overflow-clip-margin', 'border-box')) document.querySelector('#edge').textContent = 'FIT';</script>` }));
  status(await border.run(['--strict', '--widths', '320']), 0);

  const content = await fixture(t, page({ markup: `<p id="edge" style="width:100px;padding:20px;border:20px solid;white-space:nowrap;font:20px/1 monospace;overflow:clip;overflow-clip-margin:content-box">AVAILABLE</p>
    <script>if (!CSS.supports('overflow-clip-margin', 'content-box')) document.querySelector('#edge').style.padding = '0';</script>` }));
  const result = await content.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.match(result.stdout, /check=reflow element="#edge" — chữ bị cắt/);
});

test('mid-line clipping fails reflow, horizontal scrolling needs review and ellipsis passes', async (t) => {
  const clipped = await fixture(t, page({ markup: wideBox('clip', 'overflow:hidden;width:200px') }));
  const result = await clipped.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.match(result.stdout, /^✗ .*viewport=320x800 .*check=reflow element="#clip" — chữ bị cắt/m);
  assert.doesNotMatch(result.stdout, /^✗ .*viewport=1280x800 .*check=reflow/m);
  const scrollable = await fixture(t, page({ markup: wideBox('scroll', 'overflow:auto;width:200px') }));
  const scrollResult = await scrollable.run(['--widths', '320']);
  status(scrollResult, 0);
  assert.match(scrollResult.stdout, /^UNMEASURED .*viewport=320x800 .*check=reflow element="#scroll"/m);
  status(await scrollable.run(['--strict', '--widths', '320']), 1);
  const fits = await fixture(t, page({
    markup: '<div id="vertical" role="region" aria-label="More details" tabindex="0" style="overflow:auto;width:200px;height:35px"><div style="height:90px">Fits</div></div>',
  }));
  const vertical = await fits.run(['--strict', '--widths', '320']);
  status(vertical, 0);
  assert.doesNotMatch(vertical.stdout, /check=reflow/);
  const ellipsis = await fixture(t, page({ markup: '<p id="e" style="overflow:hidden;width:200px;white-space:nowrap;text-overflow:ellipsis">a very long single line of text that will be cut with an ellipsis</p>' }));
  status(await ellipsis.run(['--widths', '320']), 0);
});

test('a painted empty pseudo extending outside horizontal clipping requires reflow review', async (t) => {
  const sample = await fixture(t, page({
    css: '#edge { position: relative; overflow: hidden; width: 100%; }' +
      ' #paint::after { content: ""; position: absolute; left: 0; top: 0; width: 140%; height: 12px; background: #333; }',
    markup: '<div id="edge"><span id="paint">Text fits</span></div>',
  }));
  const result = await sample.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.match(result.stdout, /^UNMEASURED .*viewport=320x800 .*check=reflow element="#edge"/m);
});

test('visually hidden text, form fields and empty decorations are not reflow failures; a carousel is UNMEASURED', async (t) => {
  const css = '.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border-width: 0; }' +
    ' #rip { position: relative; overflow: hidden; } #rip::after { content: ""; position: absolute; top: 0; left: -50%; width: 200%; height: 100%; }';
  const benign = await fixture(t, page({
    css,
    markup: '<p>Cart <span class="sr-only">(3 items, total 42 EUR)</span></p>' +
      '<label>Email <input id="em" type="email" value="someone.with.a.long.address@example-company.example"></label>' +
      '<div id="rip">Ripple</div>',
  }));
  const ok = await benign.run(['--widths', '320']);
  status(ok, 0);
  assert.doesNotMatch(ok.stdout, /check=reflow/);
  const carousel = await fixture(t, page({
    css: '.swiper { overflow: hidden; } .wrapper { display: flex; } .slide { flex: 0 0 100%; }',
    markup: '<div class="swiper" id="car"><div class="wrapper"><div class="slide">First slide text</div><div class="slide">Second slide text</div><div class="slide">Third slide text</div></div></div>',
  }));
  const soft = await carousel.run(['--widths', '320']);
  status(soft, 0);
  assert.match(soft.stdout, /^UNMEASURED .*check=reflow element="#car" — chữ nằm ngoài khung cắt/m);
  status(await carousel.run(['--strict', '--widths', '320']), 1);
  const file = await carousel.exceptions([exception(carousel.target, { check: 'reflow', element: '#car' })]);
  const exempt = await carousel.run(['--strict', '--widths', '320', '--exceptions', file]);
  assert.match(exempt.stdout, /^EXEMPTED .*check=reflow element="#car"/m);
});

test('a measured violation is never hidden by an unmeasurable part of the same control', async (t) => {
  const sample = await fixture(t, page({
    css: '#hv:hover { background: #fff; color: #ccc; } [data-tip] { position: relative; }' +
      ' [data-tip]::after { content: attr(data-tip); position: absolute; left: 0; top: 100%; background: #111; color: #fff; opacity: 0; }' +
      ' [data-tip]:hover::after { opacity: 1; }',
    markup: '<button id="hv" data-tip="Delete item">Delete</button>',
  }));
  const result = await sample.run(['--widths', '320']);
  status(result, 1);
  assert.ok(contrastLine(result.stdout, 'state=hover') && contrastLine(result.stdout, 'element="#hv"'), result.stdout);
  assert.match(result.stdout, /^UNMEASURED .*element="#hv" — nội dung giả có nền hoặc định vị riêng/m);
});

test('an overlay pseudo-element with empty content, a filtered ancestor and a transparent iframe are UNMEASURED', async (t) => {
  const overlay = await fixture(t, page({
    css: '#ovh { position: relative; } #ovh:hover::before { content: ""; position: absolute; inset: 0; background: rgba(255,255,255,.9); }',
    markup: '<button id="ovh">Overlay</button>',
  }));
  const overlayResult = await overlay.run(['--strict', '--widths', '320']);
  status(overlayResult, 1);
  assert.match(overlayResult.stdout, /^UNMEASURED .*state=hover check=contrast element="#ovh" — nội dung giả có nền hoặc định vị riêng/m);
  const filtered = await fixture(t, page({ markup: '<div style="filter: contrast(.2)"><button id="flt">Filtered</button></div>' }));
  const filteredResult = await filtered.run(['--strict', '--widths', '320']);
  status(filteredResult, 1);
  assert.match(filteredResult.stdout, /^UNMEASURED .*check=contrast element="#flt" — độ mờ, bộ lọc/m);
  const inner = '<main><button style="background:transparent;color:#222;border:0">Pay</button></main>';
  const frame = await fixture(t, page({ css: 'body { background: #111; }', markup: `<iframe title="pay" width="200" height="80" srcdoc="${inner.replaceAll('"', '&quot;')}"></iframe>` }));
  const frameResult = await frame.run(['--strict', '--widths', '320']);
  status(frameResult, 1);
  assert.match(frameResult.stdout, /^UNMEASURED .*check=contrast element="frame\[1\] .*— khung con không có nền đục/m);
});

test('hidden descendants are not measured and an assigned slot hides its fallback content', async (t) => {
  const hidden = await fixture(t, page({ markup: '<button id="hid">Save<span style="display:none;color:#ddd">Saving</span></button>' }));
  const hiddenResult = await hidden.run(['--strict', '--widths', '320']);
  status(hiddenResult, 0);
  assert.doesNotMatch(hiddenResult.stdout, /^(?:✗|UNMEASURED) .*check=contrast/m);
  const slot = await fixture(t, page({
    markup: `<x-btn id="host">Buy now</x-btn><script>
      const root = document.getElementById('host').attachShadow({ mode: 'open' });
      root.innerHTML = '<button style="background:#fff;color:#111;min-width:48px;min-height:44px"><slot><span style="color:#eee">Default</span></slot></button>';
    </script>`,
  }));
  const slotResult = await slot.run(['--widths', '320']);
  assert.doesNotMatch(slotResult.stdout, /^✗ .*check=contrast/m);
  const dark = await fixture(t, page({
    css: 'x-card { display: block; background: #111; padding: 8px; }',
    markup: `<x-card id="card"><span id="label" style="color:#222">Slotted</span></x-card><script>
      const root = document.getElementById('card').attachShadow({ mode: 'open' });
      root.innerHTML = '<button style="background:transparent;min-width:48px;min-height:44px"><slot></slot></button>';
    </script>`,
  }));
  const darkResult = await dark.run(['--widths', '320']);
  assert.ok(contrastLine(darkResult.stdout, 'state=default'), darkResult.stdout);
});

test('right-to-left text overflowing to the left is cut, and a long page cannot hide a cut line past the scan cap', async (t) => {
  const rtl = await fixture(t, page({ markup: '<p id="rtl" dir="rtl" style="overflow:hidden;width:200px;white-space:nowrap">' + 'abcdefghij '.repeat(12) + '</p>' }));
  const rtlResult = await rtl.run(['--strict', '--widths', '320']);
  status(rtlResult, 1);
  assert.match(rtlResult.stdout, /^✗ .*viewport=320x800 .*check=reflow element="#rtl" — chữ bị cắt/m);
  const paragraphs = Array.from({ length: 260 }, (_, index) => `<p>Para ${index}</p>`).join('\n');
  const long = await fixture(t, page({ markup: `<div style="overflow-x:hidden;width:120px">${paragraphs}<p style="white-space:nowrap">Total due today: 42 EUR</p></div>` }));
  const longResult = await long.run(['--widths', '320']);
  assert.doesNotMatch(longResult.stdout, /^✓/m);
  assert.match(longResult.stdout + longResult.stderr, /^(?:✗|UNMEASURED) .*check=reflow/m);
});

test('text inside a display:contents wrapper is measured, and a page-level `parent` global does not fake a frame', async (t) => {
  const contents = await fixture(t, page({ markup: '<button id="dc"><span style="display:contents;color:#bbb">Quiet label</span></button>' }));
  const contentsResult = await contents.run(['--strict', '--widths', '320']);
  status(contentsResult, 1);
  assert.ok(contrastLine(contentsResult.stdout, 'element="#dc"'), contentsResult.stdout);
  const shadowed = await fixture(t, page({ css: 'html, body { background: transparent; }', markup: '<script>var parent = null;</script>' }));
  const shadowedResult = await shadowed.run(['--strict', '--widths', '320']);
  status(shadowedResult, 0);
  assert.doesNotMatch(shadowedResult.stdout, /khung con không có nền đục/);
});

test('a missing Chromium executable makes the real gate fail UNMEASURED', async (t) => {
  const sample = await fixture(t, page());
  const result = await sample.run(['--strict'], { ...process.env, XT_CHROMIUM: '/missing/xt-chromium' });
  status(result, 2);
  assert.match(result.stderr, /UNMEASURED.*không chạy hết cổng/);
  assert.doesNotMatch(result.stdout, /^✓/m);
});

const shadowPage = (mode, html, style = 'overflow:hidden;width:200px') => page({
  markup: `<div id="outer" tabindex="0" role="region" aria-label="shadow content" style="${style}"><x-wide id="host"></x-wide></div><script>
    const root = document.getElementById('host').attachShadow({ mode: '${mode}' });
    root.innerHTML = ${JSON.stringify(html)};
  </script>`,
});
const WIDE_IN_SHADOW = `<div style="width:900px;white-space:nowrap">${WIDE_TEXT}</div>`;

test('reflow descends into open shadow roots: cut text and a clipper inside the shadow fail, fitting text passes', async (t) => {
  const cut = await fixture(t, shadowPage('open', WIDE_IN_SHADOW));
  const cutResult = await cut.run(['--strict', '--widths', '320']);
  status(cutResult, 1);
  assert.match(cutResult.stdout, /^✗ .*viewport=320x800 .*check=reflow element="#outer" — chữ bị cắt/m);
  assert.match(cutResult.stdout, /^REFLOW .*viewport=320x800 .*shadow_measured=[1-9]\d* shadow_closed_not_measured=0$/m);
  const inner = await fixture(t, shadowPage('open', `<div id="in" style="overflow:hidden;width:200px">${WIDE_IN_SHADOW}</div>`, ''));
  const innerResult = await inner.run(['--strict', '--widths', '320']);
  status(innerResult, 1);
  assert.match(innerResult.stdout, /^✗ .*viewport=320x800 .*check=reflow element="#host >>> div#in" — chữ bị cắt/m);
  const fits = await fixture(t, shadowPage('open', '<p>Short text</p>'));
  const fitsResult = await fits.run(['--strict', '--widths', '320']);
  status(fitsResult, 0);
  assert.doesNotMatch(fitsResult.stdout, /^✗ /m);
  assert.match(fitsResult.stdout, /^REFLOW .*viewport=320x800 .*shadow_measured=[1-9]\d* shadow_closed_not_measured=0$/m);
});

test('an image sticking out of an overflow:hidden box is UNMEASURED, also inside an open shadow root', async (t) => {
  const img = `<img alt="" src="${SAMPLE_IMAGE}" width="900" height="20">`;
  const light = await fixture(t, page({ markup: `<div id="pic" tabindex="0" role="region" aria-label="picture" style="overflow:hidden;width:200px">${img}</div>` }));
  const lightResult = await light.run(['--strict', '--widths', '320']);
  status(lightResult, 1);
  assert.match(lightResult.stdout, /^UNMEASURED .*check=reflow element="#pic"/m);
  const shadow = await fixture(t, shadowPage('open', img));
  const shadowResult = await shadow.run(['--strict', '--widths', '320']);
  status(shadowResult, 1);
  assert.match(shadowResult.stdout, /^UNMEASURED .*check=reflow element="#outer"/m);
});

test('a closed shadow root cannot be measured: reported not_measured, never a pass', async (t) => {
  const closed = await fixture(t, shadowPage('closed', WIDE_IN_SHADOW));
  const result = await closed.run(['--strict', '--widths', '320']);
  status(result, 1);
  assert.match(result.stdout, /^REFLOW .*viewport=320x800 .*shadow_closed_not_measured=1$/m);
  assert.match(result.stdout, /^UNMEASURED .*check=reflow element="shadow\[closed\]" — not_measured/m);
  assert.doesNotMatch(result.stdout, /^✓/m);
});
