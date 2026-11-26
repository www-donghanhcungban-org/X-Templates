#!/usr/bin/env node
// Cổng render thật (UX-A11Y-001, 013, 028, 029). Cách dùng và mã thoát: README cùng thư mục.
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const HEIGHT = 800;
const DESKTOP = 1280;
const REFLOW_WIDTH = 400;
const THEMES = ['light', 'dark'];
const STATES = ['default', 'hover', 'focus'];
const INTERACTIVE = 'a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [role=button], [tabindex]:not([tabindex="-1"])';
const EXCEPTION_FIELDS = ['target', 'width', 'theme', 'state', 'check', 'element', 'reason', 'evidence', 'expires'];

const toUrl = (target) => /^https?:|^file:/i.test(target) ? new URL(target).href : pathToFileURL(resolve(target)).href;
const isPositiveInteger = (value) => Number.isSafeInteger(value) && value > 0;
const csv = (value) => value.split(',').map((item) => item.trim());

function options(args) {
  const { values, positionals } = parseArgs({
    args,
    allowPositionals: true,
    options: {
      widths: { type: 'string', default: '320,280' },
      themes: { type: 'string', default: 'light' },
      limit: { type: 'string', default: '60' },
      tags: { type: 'string', default: 'wcag2a,wcag2aa,wcag21aa,wcag22aa' },
      exceptions: { type: 'string' },
      strict: { type: 'boolean' },
    },
  });
  if (!positionals.length || positionals.some((target) => !target.trim())) {
    throw new Error('Thiếu đích. Dùng node verify-render.mjs <url|file.html>...');
  }
  const widths = csv(values.widths).map(Number);
  const themes = csv(values.themes);
  const limit = Number(values.limit);
  const tags = csv(values.tags);
  if (widths.some((width) => !isPositiveInteger(width))) throw new Error('--widths cần số nguyên dương');
  if (themes.some((theme) => !THEMES.includes(theme))) throw new Error('--themes chỉ nhận light,dark');
  if (!isPositiveInteger(limit)) throw new Error('--limit cần số nguyên dương');
  if (tags.some((tag) => !tag)) throw new Error('--tags cần tag axe không rỗng');
  return {
    targets: [...new Set(positionals.map(toUrl))],
    widths: [...new Set([DESKTOP, ...widths])],
    themes: [...new Set(themes)],
    limit, tags,
    exceptionsFile: values.exceptions,
    strict: values.strict,
  };
}

function dateStamp(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

const scopeKey = ({ target, width, theme, state, check, element }) => (
  JSON.stringify([target, width, theme, state, check, element])
);

function validateException(item, index) {
  const field = `exceptions[${index}]`;
  if (!item || typeof item !== 'object' || Object.keys(item).length !== EXCEPTION_FIELDS.length ||
      EXCEPTION_FIELDS.some((key) => !Object.hasOwn(item, key))) {
    throw new Error(`${field} sai cấu trúc`);
  }
  for (const key of EXCEPTION_FIELDS.filter((key) => key !== 'width')) {
    if (typeof item[key] !== 'string' || !item[key].trim()) throw new Error(`${field}.${key} cần chuỗi không rỗng`);
  }
  if (!isPositiveInteger(item.width) || !THEMES.includes(item.theme) || !STATES.includes(item.state)) {
    throw new Error(`${field} sai width, theme hoặc state`);
  }
  const axe = /^axe:[a-z0-9-]+$/.test(item.check) && item.state === 'default';
  // Dấu `*` đã escape (CSS.escape của id có sao) là ký tự thật, chỉ dấu trần mới là ký tự đại diện.
  const unescaped = item.element.replace(/\\[\s\S]/g, '');
  if ((!axe && !['contrast', 'reflow'].includes(item.check)) || item.target.includes('*') || unescaped.includes('*')) {
    throw new Error(`${field} sai check hoặc có ký tự đại diện`);
  }
  if (!dateStamp(item.expires)) throw new Error(`${field}.expires cần ngày UTC YYYY-MM-DD hợp lệ`);
  return { ...item, target: toUrl(item.target) };
}

async function readExceptions(file, today) {
  const entries = new Map();
  if (file === undefined) return entries;
  const doc = JSON.parse(await readFile(file, 'utf8'));
  if (doc?.schema !== 1 || !Array.isArray(doc.exceptions) || Object.keys(doc).length !== 2) {
    throw new Error('Tệp --exceptions cần schema 1 và mảng exceptions');
  }
  for (const [index, raw] of doc.exceptions.entries()) {
    const item = validateException(raw, index);
    const key = scopeKey(item);
    if (entries.has(key)) throw new Error(`Ngoại lệ trùng phạm vi ở exceptions[${index}]`);
    entries.set(key, { ...item, expired: item.expires < today, applied: false });
  }
  return entries;
}

// Chạy trong trang: màu chữ hiệu dụng trên nền hiệu dụng của phần tử (canvas chuyển mọi màu CSS về sRGB). Đo cả chữ của
// phần tử con và nội dung ::before/::after (mỗi phần có màu riêng), trả kết quả đo được tệ nhất; đi theo cây phẳng (slot,
// shadow host). Độ mờ, bộ lọc, hoà trộn ở bất kỳ tổ tiên nào, chữ trong suốt, pseudo có nền hay định vị riêng, khung con
// không có nền đục làm màu thật không tính được: phần đó thành `unmeasured`, nhưng vi phạm đã đo ở phần khác vẫn được trả.
const measure = (el) => {
  const ctx = Object.assign(document.createElement('canvas'), { width: 1, height: 1 }).getContext('2d', { willReadFrequently: true });
  if (!ctx) return { unmeasured: 'không đọc được màu qua canvas' };
  const rgba = (c) => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = c; ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const lum = ([r, g, b]) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const up = (n) => n.assignedSlot || n.parentElement || n.getRootNode().host || null;
  // Slot đã có nội dung gán thì phần dự phòng (con của slot) không được vẽ.
  const kids = (n) => n.localName === 'slot' && n.assignedElements().length ? n.assignedElements() : [...(n.shadowRoot ? n.shadowRoot.children : n.children)];
  const hasText = (n) => [...n.childNodes].some((c) => c.nodeType === Node.TEXT_NODE && c.textContent.trim());
  const shown = (n) => n === el || n.checkVisibility({ opacityProperty: true, visibilityProperty: true });
  const nodes = [el];
  for (let i = 0; i < nodes.length && nodes.length < 200; i++) nodes.push(...kids(nodes[i]).slice(0, 200 - nodes.length));
  const visible = nodes.filter(shown);
  const readings = visible.filter((n) => n === el || hasText(n)).map((n) => [n, null]);
  for (const node of visible.slice(0, 50)) {
    for (const pseudo of ['::before', '::after']) {
      const content = getComputedStyle(node, pseudo).content;
      if (content && !['none', 'normal'].includes(content)) readings.push([node, pseudo]);
    }
  }
  const read = ([node, pseudo]) => {
    const layers = [];
    for (let n = node; n; n = up(n)) {
      const s = getComputedStyle(n);
      if (s.opacity !== '1' || s.filter !== 'none' || s.mixBlendMode !== 'normal') return { unmeasured: 'độ mờ, bộ lọc hay chế độ hoà trộn' };
    }
    for (let n = node; n; n = up(n)) {
      const s = getComputedStyle(n);
      if (s.backgroundImage !== 'none') return { unmeasured: 'nền là ảnh/gradient' };
      const bg = rgba(s.backgroundColor);
      if (bg[3] > 0) layers.push(bg);
      if (bg[3] === 1) break;
    }
    if (layers.at(-1)?.[3] !== 1 && window.parent !== window) return { unmeasured: 'khung con không có nền đục (nền thật là trang ngoài)' };
    if (layers.at(-1)?.[3] !== 1) {
      // Canvas của trang dùng color-scheme thực tế của root, kể cả khi root và body trong suốt.
      const root = node.ownerDocument.documentElement;
      const probe = node.ownerDocument.createElement('span');
      probe.style.setProperty('all', 'initial', 'important');
      probe.style.setProperty('color-scheme', 'inherit', 'important');
      probe.style.setProperty('color', 'Canvas', 'important');
      probe.style.setProperty('display', 'none', 'important');
      root.append(probe);
      const color = getComputedStyle(probe).color;
      probe.remove();
      if (!/^(?:rgba?|color)\(/.test(color)) return { unmeasured: 'không xác định được màu Canvas của trang' };
      const canvas = rgba(color);
      if (canvas[3] !== 1) return { unmeasured: 'không xác định được màu Canvas của trang' };
      layers.push(canvas);
    }
    let base = layers.pop().slice(0, 3);
    for (const [r, g, b, a] of layers.reverse()) base = [r * a + base[0] * (1 - a), g * a + base[1] * (1 - a), b * a + base[2] * (1 - a)];
    const s = getComputedStyle(node, pseudo);
    if (pseudo && (s.backgroundImage !== 'none' || rgba(s.backgroundColor)[3] > 0 || ['absolute', 'fixed'].includes(s.position))) {
      return { unmeasured: 'nội dung giả có nền hoặc định vị riêng' };
    }
    if (pseudo && (s.opacity !== '1' || s.filter !== 'none')) return { unmeasured: 'độ mờ hoặc bộ lọc của nội dung giả' };
    if (pseudo && ['""', "''"].includes(s.content)) return { skip: true };
    const fg = rgba(s.webkitTextFillColor || s.color);
    if (fg[3] === 0) return { unmeasured: 'chữ trong suốt' };
    const text = [0, 1, 2].map((i) => fg[i] * fg[3] + base[i] * (1 - fg[3]));
    const [hi, lo] = [lum(text), lum(base)].sort((x, y) => y - x);
    const px = parseFloat(s.fontSize), bold = Number(s.fontWeight) >= 700;
    const large = px >= 24 || (px >= 18.66 && bold);
    return { ratio: (hi + 0.05) / (lo + 0.05), need: large ? 3 : 4.5 };
  };
  let worst = null, unmeasured;
  for (const item of readings) {
    const reading = read(item);
    if (reading.skip) continue;
    if (reading.unmeasured) unmeasured ??= reading.unmeasured;
    else if (!worst || reading.ratio / reading.need < worst.ratio / worst.need) worst = reading;
  }
  return { ...worst, unmeasured, label: (el.getAttribute('aria-label') || el.textContent || el.tagName).trim().slice(0, 40) };
};

// Tạo định danh ổn định cho phạm vi ngoại lệ, ưu tiên id duy nhất rồi dùng đường CSS đầy đủ.
const elementPath = (el) => {
  const parts = [];
  for (let node = el; node; node = node.parentElement) {
    const tag = CSS.escape(node.localName);
    if (node.id) {
      const id = '#' + CSS.escape(node.id);
      if (node.getRootNode().querySelectorAll(id).length === 1) {
        parts.unshift(id);
        break;
      }
    }
    let index = 1;
    for (let previous = node.previousElementSibling; previous; previous = previous.previousElementSibling) {
      if (previous.localName === node.localName) index++;
    }
    parts.unshift(`${tag}:nth-of-type(${index})`);
  }
  const root = el.getRootNode();
  return root instanceof ShadowRoot ? null : parts.join(' > ');
};

// Định danh trong báo cáo không mang userinfo, query hay fragment của đích (có thể chứa khoá hoặc phiên);
// khoá phạm vi ngoại lệ vẫn so URL đầy đủ.
function reportTarget(target) {
  const url = new URL(target);
  const hidden = Boolean(url.username || url.password || url.search || url.hash);
  url.username = '';
  url.password = '';
  url.search = '';
  url.hash = '';
  return hidden ? `${url.href}[đã che]` : url.href;
}

// Thông điệp lỗi của trình duyệt (từ chối kết nối, hết giờ) in lại nguyên URL đích: che như định danh trong báo cáo.
const URL_IN_TEXT = /\b(?:https?|file):\/\/[^\s"'<>]+(?: che\])?/gi;
function redactUrls(text) {
  return String(text).replace(URL_IN_TEXT, (raw) => {
    if (raw.endsWith(' che]')) return raw; // đã qua `reportTarget`: giữ nguyên, không che lần hai
    try {
      return reportTarget(raw);
    } catch {
      return '[url đã che]';
    }
  });
}

function scopeText({ target, width, theme, state, check, element }) {
  const group = `target=${JSON.stringify(reportTarget(target))} viewport=${width}x${HEIGHT} theme=${theme} state=${state}`;
  return check ? `${group} check=${check} element=${JSON.stringify(element)}` : group;
}

function tally() {
  return { measured: 0, unmeasured: 0, exempted: 0 };
}

function printTally(label, scope, { measured, unmeasured, exempted }) {
  console.log(`${label} ${scopeText(scope)} measured=${measured} unmeasured=${unmeasured} exempted=${exempted}`);
}

function recordUnknown(results, counts, scope, detail) {
  counts.unmeasured++;
  results.unmeasured++;
  console.log(`UNMEASURED ${scopeText(scope)} — ${detail}`);
  const exception = scope.element === null ? undefined : results.exceptions.get(scopeKey(scope));
  if (exception && !exception.expired) {
    counts.exempted++;
    results.exempted++;
    exception.applied = true;
    console.log(`EXEMPTED ${scopeText(scope)} expires=${exception.expires} reason=${JSON.stringify(exception.reason)} evidence=${JSON.stringify(exception.evidence)}`);
  }
}

function recordViolation(results, scope, detail) {
  results.violations++;
  console.log(`✗ ${scopeText(scope)} — ${detail}`);
}

const axeElement = (target) => target.length === 1 && typeof target[0] === 'string' ? target[0] : JSON.stringify(target);

async function auditAxe(page, AxeBuilder, tags, scope, results) {
  const axe = await new AxeBuilder({ page }).withTags(tags).analyze();
  const counts = tally();
  const defaultScope = { ...scope, state: 'default' };
  for (const rule of axe.passes) counts.measured += rule.nodes.length;
  for (const rule of axe.violations) {
    for (const node of rule.nodes) {
      counts.measured++;
      recordViolation(results, { ...defaultScope, check: `axe:${rule.id}`, element: axeElement(node.target) }, rule.help);
    }
  }
  for (const rule of axe.incomplete) {
    for (const node of rule.nodes) {
      recordUnknown(results, counts, { ...defaultScope, check: `axe:${rule.id}`, element: axeElement(node.target) }, rule.help);
    }
  }
  printTally('AXE', defaultScope, counts);
}

async function inState(page, control, state) {
  await page.mouse.move(-1, -1);
  await page.evaluate(() => document.activeElement?.blur?.());
  try {
    if (state === 'hover') await control.hover({ timeout: 1000 });
    if (state === 'focus') await control.focus();
  } catch (error) {
    if (page.isClosed()) throw error;
    return false;
  }
  return control.evaluate((el, expected) => {
    if (!el.isConnected) return false;
    if (expected === 'hover') return el.matches(':hover');
    if (expected === 'focus') return el.matches(':focus-visible') && !el.matches(':hover');
    return !el.matches(':hover, :focus');
  }, state);
}

// Chạy trong trang: đưa transition/animation hữu hạn về trạng thái cuối trước khi đọc màu (đo giữa chừng chuyển tiếp là
// xanh giả). Hoạt ảnh vô hạn chạm tới điều khiển (chính nó, tổ tiên hoặc con) thì màu không ổn định: báo để đánh UNMEASURED.
const settle = (el) => {
  let infinite = false;
  for (const animation of el.ownerDocument.getAnimations()) {
    const target = animation.effect?.target;
    if (animation.effect?.getComputedTiming().endTime === Infinity) {
      infinite ||= Boolean(target && (target === el || target.contains(el) || el.contains(target)));
      continue;
    }
    try {
      animation.finish();
    } catch {
      // hoạt ảnh không kết thúc được: giữ nguyên trạng thái hiện tại
    }
  }
  return infinite;
};

// Chạy trong trang: vùng nhìn thấy cắt chữ theo chiều ngang (tối đa 20), tên theo `path`. `cut`: một đoạn chữ vắt qua mép
// hộp cắt (chắc chắn mất chữ). `hidden`: chữ nằm hẳn ngoài hộp (carousel hay nội dung ẩn có chủ ý) nên cần người xem.
// Bỏ qua điều khiển form, phần tử ẩn thị giác (`clip`, `clip-path`, hộp ≤ 1 px, sr-only) và `text-overflow: ellipsis`.
const findClipped = (path) => {
  const found = [];
  const visible = (n) => n.checkVisibility({ opacityProperty: true, visibilityProperty: true });
  for (const el of document.querySelectorAll('*')) {
    const s = getComputedStyle(el);
    if (!['hidden', 'clip'].includes(s.overflowX) || s.textOverflow === 'ellipsis') continue;
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) || el.clientWidth <= 1 || el.scrollWidth <= el.clientWidth + 1) continue;
    if (s.clip !== 'auto' || s.clipPath !== 'none' || !visible(el)) continue;
    const box = el.getBoundingClientRect();
    let kind = null;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(), seen = 0; node && kind !== 'cut' && seen < 500; node = walker.nextNode(), seen++) {
      if (!node.textContent.trim() || !visible(node.parentElement)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.width > 0 && rect.right > box.right + 1) kind = rect.left < box.right - 1 ? 'cut' : (kind ?? 'hidden');
      }
    }
    if (kind) found.push({ element: path(el) ?? el.localName, kind });
    if (found.length === 20) break;
  }
  return found;
};

async function auditContrast(page, scope, results, limit) {
  const counts = new Map(STATES.map((state) => [state, tally()]));
  // Mỗi khung (iframe, kể cả lồng nhau) có cây DOM riêng: bộ chọn của trang không đi vào khung nên duyệt từng khung.
  const controls = [];
  for (const [index, frame] of page.frames().entries()) {
    for (const handle of await frame.locator(INTERACTIVE).elementHandles()) controls.push({ handle, frame: index });
  }
  let visible = 0;
  for (const { handle: control, frame } of controls) {
    // Điều khiển vô hiệu (kể cả kế thừa từ fieldset disabled) không nhận focus nên không thuộc phạm vi đo.
    if (!await control.isVisible() || await control.evaluate((el) => el.matches(':disabled'))) continue;
    const path = await control.evaluate(elementPath);
    const element = path === null || !frame ? path : `frame[${frame}] ${path}`; // null (shadow root) giữ nguyên: không khai ngoại lệ được
    visible++;
    for (const state of STATES) {
      const row = counts.get(state);
      const check = { ...scope, state, check: 'contrast', element };
      if (visible > limit) {
        recordUnknown(results, row, check, 'vượt --limit');
        continue;
      }
      if (!await inState(page, control, state)) {
        recordUnknown(results, row, check, 'không kích hoạt được trạng thái');
        continue;
      }
      if (await control.evaluate(settle)) {
        recordUnknown(results, row, check, 'hoạt ảnh vô hạn đang chạy trên điều khiển');
        continue;
      }
      const reading = await control.evaluate(measure);
      // Vi phạm đã đo luôn được báo, kể cả khi một phần khác của điều khiển không đo được (không để UNMEASURED che vi phạm).
      if (reading.ratio !== undefined) {
        row.measured++;
        if (reading.ratio < reading.need) {
          const ratio = (Math.floor(reading.ratio * 100) / 100).toFixed(2);
          recordViolation(results, check, `${JSON.stringify(reading.label)} ${ratio}:1 < ${reading.need}:1`);
        }
      }
      if (reading.unmeasured) recordUnknown(results, row, check, reading.unmeasured);
    }
  }
  for (const [state, row] of counts) printTally('CONTRAST', { ...scope, state }, row);
}

async function auditPage(browser, AxeBuilder, settings, scope, results) {
  const context = await browser.newContext({
    viewport: { width: scope.width, height: HEIGHT },
    colorScheme: scope.theme,
  });
  try {
    const page = await context.newPage();
    const response = await page.goto(scope.target);
    // Trang lỗi HTTP không được báo đạt: file: trả null, còn http(s) phải là 2xx sau chuyển hướng.
    if (response && !response.ok()) throw new Error(`HTTP ${response.status()} tại ${reportTarget(scope.target)}`);
    await auditAxe(page, AxeBuilder, settings.tags, scope, results);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    if (overflow > 0) {
      recordViolation(results, { ...scope, state: 'default', check: 'reflow', element: 'html' }, `tràn ngang +${overflow}px`);
    }
    // Reflow (WCAG 1.4.10) ở khổ hẹp: vùng `overflow:hidden|clip` mà nội dung rộng hơn khung thì phần thừa bị cắt chứ
    // không cuộn, nên `scrollWidth` của gốc không thấy. Cắt chữ có chủ ý bằng `text-overflow:ellipsis` thì bỏ qua.
    if (scope.width <= REFLOW_WIDTH) {
      for (const { element, kind } of await page.evaluate(`(${findClipped})(${elementPath})`)) {
        const clipped = { ...scope, state: 'default', check: 'reflow', element };
        if (kind === 'cut') recordViolation(results, clipped, 'chữ bị cắt ngang bởi overflow:hidden');
        else recordUnknown(results, tally(), clipped, 'chữ nằm ngoài khung cắt (carousel hay nội dung ẩn có chủ ý?), cần người xem');
      }
    }
    await auditContrast(page, scope, results, settings.limit);
  } finally {
    await context.close();
  }
}

async function run(settings, results) {
  // Nạp sau khi kiểm cấu hình để lỗi thiếu phụ thuộc luôn báo UNMEASURED.
  const [{ chromium }, { default: AxeBuilder }] = await Promise.all([
    import('playwright'), import('@axe-core/playwright'),
  ]);
  const browser = await chromium.launch({ executablePath: process.env.XT_CHROMIUM || undefined });
  try {
    for (const target of settings.targets) {
      for (const theme of settings.themes) {
        for (const width of settings.widths) await auditPage(browser, AxeBuilder, settings, { target, width, theme }, results);
      }
    }
  } finally {
    await browser.close();
  }
}

function conclusion(settings, results) {
  for (const item of results.exceptions.values()) {
    const state = item.expired ? 'EXPIRED' : !item.applied ? 'UNUSED' : '';
    if (state) console.log(`EXCEPTION ${state} ${scopeText(item)} expires=${item.expires}`);
  }
  const outstanding = results.unmeasured - results.exempted;
  console.log(`Kết quả: ${results.violations} vi phạm, ${results.unmeasured} UNMEASURED (${results.exempted} có ngoại lệ, ${outstanding} chưa miễn).`);
  if (results.violations || (settings.strict && outstanding > 0)) return 1;
  if (results.unmeasured === 0) console.log(`✓ ${settings.targets.length} trang đạt (axe, reflow, tương phản theo trạng thái).`);
  return 0;
}

async function main() {
  let settings, exceptions;
  try {
    settings = options(process.argv.slice(2));
    exceptions = await readExceptions(settings.exceptionsFile, new Date().toISOString().slice(0, 10));
  } catch (error) {
    console.error(`Cấu hình không hợp lệ: ${redactUrls(error.message)}`);
    return 2;
  }
  const results = { exceptions, violations: 0, unmeasured: 0, exempted: 0 };
  try {
    await run(settings, results);
  } catch (error) {
    console.error(`UNMEASURED — không chạy hết cổng: ${redactUrls(error.message)}`);
    return 2;
  }
  return conclusion(settings, results);
}

process.exitCode = await main();
