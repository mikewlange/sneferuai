// Focused behavior tests for the progressive motion enhancement; browser
// layout and native video playback are checked separately in the preview.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../assets/site.js'), 'utf8');

function boot({reduced = false, observer = true, labelPresent = true, iconPresent = true} = {}) {
  const events = {};
  const media = {matches: reduced, addEventListener: (_, handler) => { events.media = handler; }};
  const label = {};
  const icon = {};
  const button = {
    attrs: {},
    setAttribute(name, value) { this.attrs[name] = value; },
    querySelector(selector) { return selector === '.motion-label' ? (labelPresent ? label : null) : (iconPresent ? icon : null); },
    addEventListener(_, handler) { events.click = handler; },
  };
  const classes = new Set();
  const element = {
    classList: {add: (...names) => names.forEach(name => classes.add(name)), remove: name => classes.delete(name)},
    getBoundingClientRect: () => ({top: 900}),
  };
  const panels = ['software', 'business', 'research', 'games'].map((name, index) => ({
    id: `panel-${name}`, hidden: index !== 0, pauses: 0,
    querySelectorAll() { return name === 'games' ? [{pause: () => { this.pauses++; }}] : []; },
  }));
  const tabs = panels.map((panel, index) => ({
    attrs: {'aria-controls': panel.id, 'aria-selected': String(index === 0)},
    tabIndex: index === 0 ? 0 : -1, events: {},
    setAttribute(name, value) { this.attrs[name] = value; },
    getAttribute(name) { return this.attrs[name]; },
    addEventListener(name, handler) { this.events[name] = handler; },
    focus() { this.focused = true; },
  }));
  const document = {
    documentElement: {dataset: {}},
    querySelector: selector => selector === '.motion-toggle' ? button : null,
    querySelectorAll: selector => selector.startsWith('.split-heading') ? [element] : selector === '[role="tablist"]' ? [{querySelectorAll: () => tabs}] : [],
    getElementById: id => panels.find(panel => panel.id === id),
    addEventListener: (name, handler) => { events[name] = handler; },
  };
  const window = {innerHeight: 800, matchMedia: query => query.includes('reduced-motion') ? media : {addEventListener() {}}};
  class IntersectionObserver {
    constructor(callback) { events.intersection = callback; }
    observe() {}
    unobserve() {}
  }
  if (observer) window.IntersectionObserver = IntersectionObserver;
  vm.runInNewContext(source, {window, document, IntersectionObserver});
  return {document, events, media, button, label, classes, element, tabs, panels};
}

function assertSelected(state, index) {
  state.tabs.forEach((tab, i) => {
    assert.equal(tab.attrs['aria-selected'], String(i === index));
    assert.equal(tab.tabIndex, i === index ? 0 : -1);
    assert.equal(state.panels[i].hidden, i !== index);
  });
}

test('the actual homepage motion-button markup does not prevent tab initialization', () => {
  const home = readFileSync(resolve(__dirname, '../../index.html'), 'utf8');
  const control = home.match(/<button\b[^>]*class="motion-toggle"[^>]*>[\s\S]*?<\/button>/)[0];
  const state = boot({labelPresent: control.includes('class="motion-label"'), iconPresent: control.includes('class="motion-icon"')});
  state.tabs.forEach((tab, index) => { tab.events.click(); assertSelected(state, index); });
});

test('optional motion-label and icon cannot break clicks or keyboard tab selection', () => {
  for (const reduced of [false, true]) {
    for (const [labelPresent, iconPresent] of [[false, true], [true, false], [false, false]]) {
      const state = boot({reduced, labelPresent, iconPresent});
      state.tabs[1].events.click();
      assertSelected(state, 1);
      let prevented = false;
      state.tabs[1].events.keydown({key: 'End', preventDefault() { prevented = true; }});
      assert.ok(prevented);
      assertSelected(state, 3);
      assert.ok(state.tabs[3].focused);
      state.tabs[3].events.keydown({key: 'ArrowDown', preventDefault() {}});
      assertSelected(state, 0);
      assert.ok(state.panels[3].pauses > 0, 'leaving Games pauses its video');
      state.events.click();
      assert.equal(state.button.attrs['aria-pressed'], 'true');
      state.tabs[2].events.click();
      assertSelected(state, 2);
    }
  }
});

test('visitor can pause and resume; pausing reveals every pending section', () => {
  const state = boot();
  assert.equal(state.document.documentElement.dataset.motion, 'on');
  assert.ok(state.classes.has('motion-pending'));
  state.events.click();
  assert.equal(state.document.documentElement.dataset.motion, 'off');
  assert.equal(state.button.attrs['aria-pressed'], 'true');
  assert.equal(state.label.textContent, 'Motion off');
  assert.ok(!state.classes.has('motion-pending'));
  state.events.click();
  assert.equal(state.document.documentElement.dataset.motion, 'on');
});

test('reduced-motion preference disables decorative movement from the start', () => {
  const state = boot({reduced: true});
  assert.equal(state.document.documentElement.dataset.motion, 'off');
  assert.equal(state.button.disabled, true);
  assert.equal(state.label.textContent, 'Reduced motion');
  assert.ok(!state.classes.has('motion-pending'));
});

test('changing the system motion preference reveals pending content', () => {
  const state = boot();
  state.media.matches = true;
  state.events.media();
  assert.equal(state.document.documentElement.dataset.motion, 'off');
  assert.ok(!state.classes.has('motion-pending'));
});

test('intersection and keyboard focus each reveal the destination', () => {
  const first = boot();
  first.events.intersection([{isIntersecting: true, target: first.element}]);
  assert.ok(!first.classes.has('motion-pending'));
  const second = boot();
  second.events.focusin({target: {closest: () => second.element}});
  assert.ok(!second.classes.has('motion-pending'));
});

test('content stays visible if intersection observers are unavailable', () => {
  const state = boot({observer: false});
  assert.ok(!state.classes.has('motion-pending'));
});

// ── The run panel: one Sneferu run played as five scenes, under the same motion controls.
function fakeElement(extra = {}) {
  const classes = new Set();
  return {
    classes, textContent: '', dataset: {}, hidden: false,
    style: {props: {}, setProperty(name, value) { this.props[name] = value; }, removeProperty(name) { delete this.props[name]; }},
    classList: {
      add: (...names) => names.forEach(name => classes.add(name)),
      remove: (...names) => names.forEach(name => classes.delete(name)),
      toggle(name, force) { const on = force === undefined ? !classes.has(name) : force; on ? classes.add(name) : classes.delete(name); return on; },
      contains: name => classes.has(name),
    },
    addEventListener() {},
    ...extra,
  };
}

function bootRun({reduced = false} = {}) {
  const events = {};
  const timers = {timeouts: [], intervals: []};
  const media = {matches: reduced, addEventListener: (_, handler) => { events.media = handler; }};
  const label = {}; const icon = {};
  const button = fakeElement({attrs: {}, setAttribute(name, value) { this.attrs[name] = value; }, querySelector: s => s === '.motion-label' ? label : icon, addEventListener: (_, handler) => { events.click = handler; }});
  const scenes = [0, 1, 2, 3, 4].map(i => fakeElement({dataset: {status: `status ${i}`}}));
  const rail = [0, 1, 2, 3, 4].map(() => fakeElement());
  const state = fakeElement(); const status = fakeElement();
  const typed = fakeElement(); typed.textContent = 'Build me a thing.';
  const replay = fakeElement({addEventListener: (_, handler) => { events.replay = handler; }});
  const run = fakeElement({
    querySelectorAll: selector => selector === '.run-scene' ? scenes : selector === '.run-rail li' ? rail : [],
    querySelector: selector => ({'[data-run-state]': state, '[data-run-status]': status, '[data-run-type]': typed, '[data-run-replay]': replay})[selector] || null,
  });
  const document = {
    documentElement: {dataset: {}}, hidden: false,
    querySelector: selector => selector === '.motion-toggle' ? button : selector === '[data-run]' ? run : null,
    querySelectorAll: () => [],
    addEventListener: (name, handler) => { events[name] = handler; },
  };
  const window = {
    innerHeight: 800,
    matchMedia: query => query.includes('reduced-motion') ? media : {addEventListener() {}},
    setTimeout: (fn, ms) => { timers.timeouts.push({fn, ms}); return timers.timeouts.length; },
    clearTimeout: () => {},
    setInterval: (fn, ms) => { timers.intervals.push({fn, ms}); return timers.intervals.length; },
    clearInterval: () => {},
  };
  vm.runInNewContext(source, {window, document});
  return {events, timers, run, scenes, rail, state, status, typed, document};
}

test('the run panel starts at the request, then advances scene by scene on its timer', () => {
  const s = bootRun();
  assert.equal(s.run.classes.has('is-static'), false);
  assert.ok(s.scenes[0].classes.has('is-active'));
  assert.ok(s.rail[0].classes.has('is-active'));
  assert.equal(s.state.textContent, 'Request');
  assert.equal(s.status.textContent, 'status 0');
  assert.equal(s.run.style.props['--run-progress'], '20%');
  assert.equal(s.timers.intervals.length, 1, 'the request is typed out');
  const next = s.timers.timeouts.at(-1);
  assert.equal(next.ms, 3000);
  next.fn();
  assert.ok(s.scenes[1].classes.has('is-active'));
  assert.ok(!s.scenes[0].classes.has('is-active'));
  assert.ok(s.rail[0].classes.has('is-done'));
  assert.equal(s.state.textContent, 'Propose');
});

test('pausing motion settles the run panel on its finished state with the whole request visible', () => {
  const s = bootRun();
  s.typed.textContent = 'Build';
  s.events.click();
  assert.ok(s.run.classes.has('is-static'));
  assert.equal(s.typed.textContent, 'Build me a thing.');
  assert.equal(s.state.textContent, 'Finished');
  assert.ok(s.rail.every(item => item.classes.has('is-done') && !item.classes.has('is-active')));
  assert.ok(s.scenes.every(scene => !scene.classes.has('is-active')));
  s.events.click();
  assert.ok(!s.run.classes.has('is-static'));
  assert.ok(s.scenes[0].classes.has('is-active'));
});

test('reduced motion never starts the run panel timers', () => {
  const s = bootRun({reduced: true});
  assert.equal(s.timers.timeouts.length, 0);
  assert.equal(s.timers.intervals.length, 0);
  assert.equal(s.state.textContent, 'Finished');
  assert.ok(s.run.classes.has('is-static'));
});

test('replay restarts from the request; a hidden tab stops the clock', () => {
  const s = bootRun();
  s.timers.timeouts.at(-1).fn();
  assert.equal(s.state.textContent, 'Propose');
  s.events.replay();
  assert.equal(s.state.textContent, 'Request');
  const before = s.timers.timeouts.length;
  s.document.hidden = true;
  s.events.visibilitychange();
  assert.equal(s.timers.timeouts.length, before, 'a hidden tab schedules nothing');
  s.timers.timeouts.at(-1).fn();
  s.document.hidden = false;
  s.events.visibilitychange();
  assert.equal(s.state.textContent, 'Request', 'coming back starts the run again from the request');
  assert.ok(s.timers.timeouts.length > before + 1);
});
