# Public-site node purchase

The offer at `/sod/` and status page at `/sod/launching/?o=<token>` use the
existing guest node-order API. The browser goes to Stripe for payment and
returns to sneferu.ai; it never navigates to the storefront's own signup page.

## Deployment settings and release order

`STORE_ORIGIN` is the single backend setting in each page. Both currently name
Public Works as the proposed storefront. Mike must confirm that choice before
activation; no backend configuration is changed by this website commit.

1. Deploy the matching claudopus backend with `node_offer.site_origin` support.
2. In the storefront's Billing & plans, set Public site origin to
   `https://sneferu.ai`. Review the actual recurring Stripe price, markup,
   rate hold and terms. The page reads these values; it contains no price.
3. Prepare the launcher's storefront and reviewed purchased-node template:
   billing off on the node, invitation-only, account limit one. Keep existing
   test nodes and Public Works account policy unchanged.
4. Complete the Stripe test-mode purchase, disposable-node launch, invitation
   receipt and sign-in proof, including a real phone running Safari. Then
   complete Mike's authorized live purchase/refund before opening public sales.
5. Only publish these pages and enable the offer after that release approval.
   A push to this repository's `main` publishes through GitHub Pages.

The backend can leave the offer disabled throughout preparation. The page
disables new purchases when the offer is off, missing or unavailable. A saved
attempt in this tab can use **Resume saved checkout** with its original name
and email; the backend confirms the existing order and its original terms.
Changing the buyer disables that closed-offer retry. No new request identity is
created while sales are closed. Existing buyers can also open their order and
billing when new sales are closed.

## Important behavior

- Cross-origin fetches omit cookies, referrers and redirects. Only the exact
  configured public origin can read the four guest API routes. No trackers,
  third-party scripts or Formspree submissions run on either purchase page.
- Name, email and the checkout attempt key are saved in sessionStorage before
  the first POST. Lost replies and reloads reuse the key. A completed order
  clears the attempt after the API confirms its identity and payment state.
- The status response never exposes email. The exact saved address is shown
  only when this browser's purchase matches the returned order ID; another
  device gets “the address you used at checkout.” Invitation delivery is the
  launcher's responsibility and must be proven separately in the live test.
- The page follows the API's `open_url`; it never constructs a node address.
  A missing/malformed address keeps polling and shows a recovery message.
- Normal polling is every five seconds; rate limiting waits a minute.
  Interrupted requests retry, while an unknown order offers “Check again” and
  help without prompting the buyer to pay again.

## Local checks

```sh
python3 -m unittest discover -s .github/scripts -p 'test_*.py'
python3 -m unittest discover -s v2/.github/scripts -p 'test_*.py'
node --test .github/scripts/test_site_motion.cjs
node --test v2/.github/scripts/test_site_motion.cjs
python3 -m pip install -r .github/browser-requirements.txt
python3 -m playwright install chromium webkit
python3 -m pytest .github/scripts/purchase_browser_checks.py -q
python3 .github/scripts/build_site.py
python3 .github/scripts/validate_site.py --root _site
```

Browser checks use local API, payment and launcher fixtures; all requests are
intercepted. They prove the shipped pages, responsive layout, retries and
navigation in Chromium/WebKit. They do not prove live payment, cloud capacity,
email receipt, physical-phone behavior or the private node's first login.

## October 7 final review follow-through

The backend already admitted existing purchase retries after sales closed, but
the website disabled their button. The new browser reproduction failed in both
Chromium and WebKit before the fix (four cases: a closed offer and a 503 in each
engine). It now passes without changing existing assertions. It also proves
that changing the buyer cannot submit a new purchase and that restoring the
original buyer reuses the exact request key after a lost reply.

The final pass also covers the backend’s actual closed-offer HTTP 404 response.
Verification on this change: 62 purchase browser checks; main/V2 Python and
motion checks; public artifact build and validation (267 files). All local,
with payment/cloud/API fixtures. No push, publication or real payment.
