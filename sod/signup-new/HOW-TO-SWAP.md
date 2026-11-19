# New SOD sign-up page: draft, not live (Nov 13 2026)

This folder (`sod/signup-new/`) holds the redo of `sod/signup/index.html`. It is a draft. It is untracked, and the site build publishes only files that git tracks, so it is not published unless someone adds it to git. If it were added and pushed by accident, it would appear at the unlisted address /sod/signup-new/ and work like the real page.

## What is where

- `index.html` in this folder: the new page. It uses the same paths as the real page, so swapping it in is a plain copy.
- `assets/sod-signup/` at the repo root: the six screenshots the page shows (request, cast, debate, preview, research, saved-cast). They are untracked until someone adds them.

## To make it live (three steps, then commit and push)

1. Copy this `index.html` over `sod/signup/index.html`.
2. In `.github/scripts/purchase_browser_checks.py`, line 129, change the expected button text
   from `Launch your node — $2,123.50/month`
   to `Launch my VM, $2,123.50/month`.
3. `git add assets/sod-signup` so the six images are published. Without them the site validator fails with "broken local reference" and nothing deploys.

## What changed in the checkout script (text only, plus two display lines)

- Button label: "Launch my VM, $999/month" (was "Launch your node" with a long dash). Two places.
- Fallback plan name: "Your private VM".
- Bill explanation sentence: "covers your private VM".
- Already-complete message: "Use your VM invitation email to sign in."
- Two added lines in `loadOffer`: every element marked `data-offer-price` or `data-offer-markup` gets the confirmed price and premium, so the hero line, the matrix and the last card can never disagree with the form.
- Nothing else in the script was touched. Form field names, ids, the API calls and the saved-attempt logic are byte for byte the same.

## Tests run on Nov 13 (in Claude's workspace, Chromium only)

- `test_purchase_contract.py`: 3 of 3 pass.
- `purchase_browser_checks.py`, Chromium: 43 pass, 2 fail.
- The same 2 fail on the untouched original files in the same workspace. Both are about the launching page (`#lvEmail`), which this work did not touch:
  `test_checkout_paid_phases_ready_then_billing_without_backend_navigation` and `test_ready_on_another_device_does_not_invent_email`.
  The workspace has Playwright 1.63, the repo pins 1.62, so this may be the workspace and not the repo.
- WebKit was not run (not installed in the workspace). CI runs it on push.
- Site validator rules for the sign-up page (one form, ids, honeypot, links, anchors, images): pass.
- Phone, 390 by 844: the launch button ends at 775, above the fold limit of 844 that the test checks.

## Still says "node" elsewhere

- The launching page, the invitation email, and any plan name the server returns (for example a Stripe product name).
