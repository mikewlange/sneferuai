// Focused behavior tests for the progressive motion enhancement; browser
// layout and native video playback are checked separately in the preview.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const vm = require('node:vm');
const source = readFileSync(resolve(__dirname, '../../assets/site.js'), 'utf8');

function boot({reduced = false, observer = true} = {}) {
  const events = {};
  const media = {matches: reduced, addEventListener: (_, handler) => { events.media = handler; }};
  const label = {};
  const icon = {};
  const button = {
    attrs: {},
    setAttribute(name, value) { this.attrs[name] = value; },
    querySelector(selector) { return selector === '.motion-label' ? label : icon; },
    addEventListener(_, handler) { events.click = handler; },
  };
  const classes = new Set();
  const element = {
    classList: {add: (...names) => names.forEach(name => classes.add(name)), remove: name => classes.delete(name)},
    getBoundingClientRect: () => ({top: 900}),
  };
  const document = {
    documentElement: {dataset: {}},
    querySelector: selector => selector === '.motion-toggle' ? button : null,
    querySelectorAll: selector => selector.startsWith('.split-heading') ? [element] : [],
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
  return {document, events, media, button, label, classes, element};
}

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
