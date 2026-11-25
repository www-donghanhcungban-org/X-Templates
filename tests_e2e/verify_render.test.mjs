import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
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

function page({ narrowCSS = '', markup = '' } = {}) {
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
    async run(args = [], env = process.env) {
      try {
        const { stdout, stderr } = await execute(process.execPath, [script, sample, ...args], { cwd: root, env });
        return { code: 0, stdout, stderr };
      } catch (error) {
        if (typeof error.code !== 'number') throw error;
        return { code: error.code, stdout: error.stdout, stderr: error.stderr };
      }
    },
  };
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
    { width: 320.5 }, { check: 'reflow' }, { element: '*' },
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

test('a missing Chromium executable makes the real gate fail UNMEASURED', async (t) => {
  const sample = await fixture(t, page());
  const result = await sample.run(['--strict'], { ...process.env, XT_CHROMIUM: '/missing/xt-chromium' });
  status(result, 2);
  assert.match(result.stderr, /UNMEASURED.*không chạy hết cổng/);
  assert.doesNotMatch(result.stdout, /^✓/m);
});
