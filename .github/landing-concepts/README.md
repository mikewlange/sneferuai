# Five simpler Sneferu landing pages

Local design candidates requested November 13, 2026. These files live under
`.github/`, which the existing publication builder excludes. The live homepage,
Software On Demand pages, pricing and existing staged email-label edit are unchanged.

## Direction

Lead with what a customer gets: describe a need, approve a plan, try the working
software. Mention rival AI models and autonomous coders once. Invite a demo.
Leave architecture, research results, long history, internal terminology and
detailed workflow demonstrations out of the first visit. Avoid guarantees of
perfection or universal results.

The current public homepage, Inside Sneferu, archived field notes and SOD page
were fetched and compared with this checkout; all four matched. The homepage
contains approximately 2,131 extracted words including dialogs. SOD's narrative
is supplied by its inline `SOD_COPY` object. The alternatives below contain
48–113 words in their main content, excluding shared navigation and demo form.

| Design | Approach | Main words |
| --- | --- | ---: |
| 01 / Limestone | Warm editorial page, copper pyramid, three concise steps | 81 |
| 02 / Night | Dark, single invitation, shortest copy | 48 |
| 03 / Copper | Typographic brand poster | 57 |
| 04 / The short story | Three scrolling chapters and a progressively assembled pyramid | 113 |
| 05 / In your hands | Three large editorial chapters on paper, sage and copper | 103 |

Recommendation: 01 for the clearest introduction; 04 for a restrained version
of the existing SOD scrolling experience. The comparison index links to each.

## Preview

From the repository root:

```sh
python3 -m http.server 0 --bind 127.0.0.1 --directory .github/landing-concepts
```

Open the printed local address. The pages are buildless and also support direct
HTML-file viewing. All fonts, brand assets and illustrations are local. DM Sans
and Newsreader are distributed with their SIL Open Font Licenses in `assets/`.
Brand logos are copied from the existing site's assets. The geometric artwork
is original inline SVG, with no generated product screenshots or invented proof.

Demo buttons open an accessible native dialog. Forms use the existing website's
Formspree destination and are labeled as demo requests. Tests intercept every
submission; no real test messages are sent. With JavaScript off, the same links
open an email draft to the established founder address. Scroll animations respect
reduced-motion preferences and do not intercept or lock scrolling.

## Checks

Use the repository's `.github/browser-requirements.txt` dependencies and installed
Chromium/WebKit browsers:

```sh
python -m pytest .github/landing-concepts/checks.py -q
```

Checks cover desktop and phone widths, local asset loading, concise HTML content,
JavaScript-off use, demo request success and failure with local responses, focus
restoration, Escape, reduced motion, scroll progress, and all gallery links.
Desktop and mobile screenshots are inspected separately. Formspree delivery is
not exercised by these checks.
