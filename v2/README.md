# Sneferu website, V2

Dark, animated, platform-first. Upgraded September 24, 2026: new copy, constant names,
a product surface in the hero, and restrained SOD-style motion.
This is a self-contained copy of the site, not a deployment.

## What changed on September 24

- `index.html`: rewritten. The category headline ("The operating system for finished work") with
  the promise as its tag ("The best version of your idea"), an animated
  run panel that plays one Sneferu run in five scenes (request → propose → challenge →
  prove → finish), a strip of the finished products' logos (each linking to its
  GitHub repository; Software On Demand to `/sod/`), three "why" cards, the four
  production lines as tabs, the engine, the Bent Pyramid origin, the builds, SOD, FAQ,
  the bet, contact. All five example dialogs are kept.
- `system.html`: rewritten as a plain-English tour, one named part per section, in the
  Atlas's order: Snef, the engine, Sneferu Coders, the production lines, ESM, Run Truth,
  the Fleet, the models.
- `assets/site.css`: new stylesheet on the brand values (night `#0E0F13`, limestone
  `#F3EEE2`, copper `#E2946C`), Inter / Newsreader / JetBrains Mono, all motion gated by
  `[data-motion]` and `prefers-reduced-motion`. No GSAP; no external scripts.
- `assets/logos/`: the product logos in the strip (PNG, the products' own colours).
- `assets/site.js`: run-panel scheduler (pauses off-screen and in hidden tabs, settles
  to the finished state when motion is off), ticker, scroll reveals, nav, tabs, dialogs,
  contact form. `site.js` is still the only script either page loads.
- `assets/sneferu-mark-on-dark.svg`: the approved mark, copied from the brand vector kit.
- `.github/scripts/`: the site's own tests, extended: constant-name checks (retired names
  such as "Game Studio" and "Build-a-Business" fail the build; "Sneferu Brain" may only
  follow "Snef"), do-not-say phrases from the proof-points sheet, run-panel structure and
  behaviour, ticker labels, and the system-page tour index.

## Constant names (use these everywhere)

Sneferu (the system) · Snef (the operator; introduced once as the Sneferu Brain) ·
adversarial convergence (the engine) · Sneferu Coders · Idea Bloom · Business Autopilot ·
Research Expedition · Game Autopilot · Goal Master · Problem Solver · Demo Studio ·
Spec Factory · ESM (memory) · Run Truth (the receipts) · the Fleet · Software On Demand.

## Test this copy

```sh
cd /Users/sneferumain/sneferuai/v2
python3 -m unittest discover -s .github/scripts -p 'test_*.py'
node --test .github/scripts/test_site_motion.cjs
python3 .github/scripts/validate_site.py --root .
```

## Preview this copy

```sh
cd /Users/sneferumain/sneferuai/v2
python3 -m http.server 8766 --bind 127.0.0.1
```

Then open <http://127.0.0.1:8766/>. Serve this folder as the site root;
root-relative links will not work by double-clicking the HTML file
or serving it under a `/v2/` URL prefix.

The contact form retains the real Formspree destination. Do not submit test
messages unless you intend to send them. No confidential documents are included.

Nothing has been committed, pushed, or published, and no application or fleet
configuration was changed. To go live: copy `index.html`, `system.html`, `assets/site.css`,
`assets/site.js`, `assets/sneferu-mark-on-dark.svg`, and the three files in
`.github/scripts/` over the repo root, run the tests above from the root, then push.
