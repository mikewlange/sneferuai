# sneferu.ai

The production repository for [sneferu.ai](https://sneferu.ai/).

## Release path

`main` is the only publishing branch. Every push builds a clean public artifact,
checks its pages, links, media, contact form, custom domain, and file limits, and
deploys to GitHub Pages only after those checks pass. Pull requests run the same
build and validation without publishing.

The GitHub Pages artifact deliberately excludes this README, repository tooling,
and workflow files. It preserves the public `research/` archive, `CNAME`, and
`.nojekyll`.

## Website structure

- `index.html`: the selected V2 design, promoted to the main landing page.
- `system.html`: V2's plain-language explanation of the engines, Snef, and fleet.
- `field-notes.html`: the preserved previous homepage and its detailed records,
  labeled as an archive rather than current operating status. It stays saved,
  but the new homepage and system page do not link to it.
- `sod/index.html`: the existing Software On Demand product page, unchanged.
- `atlas-preview.html` and `research/`: existing public reference material.
- `v2/assets/`: shared V2 styles, scripts, logos, and media used by the new root
  pages and `/v2/`. CSS and JavaScript URLs include content-hash cache versions.
- `assets/site.css` and `assets/site.js`: retained unchanged for `/v3/` and other
  existing pages. No framework or application backend is required.

The root overview pages match the V2 copies except for their asset prefix
(`v2/assets/` at the root, `assets/` within V2). Tests enforce that relationship.
When updating these pages, keep both copies aligned. When editing V2 CSS or JS,
refresh their `?v=` values with the first 12 characters of the file's SHA-256 hash.

The dark overview features ESM-Gateway and HungerHall alongside the existing
product examples. ESM visuals describe the memory architecture, not a live feed.
HungerHall uses the existing gameplay recording and the founder's first-playthrough
quote. Decorative motion can be paused on either page and respects the visitor's
reduced-motion preference. Videos are user-initiated and pause when their dialog
or workflow tab closes.

## Local preview

Build with `python3 .github/scripts/build_site.py`, then check the artifact with
`python3 .github/scripts/validate_site.py --root _site`.
Run the safety and markup checks with
`python3 -m unittest discover -s .github/scripts -p 'test_*.py'`.
Run motion behavior checks with `node --test .github/scripts/test_site_motion.cjs`.
Also run the selected design's checks:

```sh
python3 -m unittest discover -s v2/.github/scripts -p 'test_*.py'
node --test v2/.github/scripts/test_site_motion.cjs
```

Before new public files are tracked, pass an explicit `--include relative/file`
for each one. The builder never discovers or publishes untracked files implicitly.
All landing-page files are already tracked. The preview uses:

```sh
python3 .github/scripts/build_site.py
python3 .github/scripts/validate_site.py --root _site
python3 -m http.server 8765 --bind 127.0.0.1 --directory _site
```

Serve only `_site`, not the repository root: unrelated private documents may be
present in the working directory. This preview does not publish or change SOD,
the coordinator, fleet, or customer runs. Contact submissions use the existing
Formspree endpoint; do not send test enquiries to it.
