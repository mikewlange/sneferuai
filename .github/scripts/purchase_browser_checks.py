"""Two real browser engines, shipped HTML, local response fixtures only.

The API/Stripe/launcher are simulated here. Backend route tests prove CORS and
payment-ledger semantics separately. These checks cannot prove a live charge,
a cloud launch, email delivery, or use on a physical iPhone.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SITE = "https://sneferu.ai"
STORE = "https://sod.sneferu.ai"
API = STORE + "/api/sod/node-offer"
TOKEN = "a" * 40
ATTEMPT = "sneferu.node-purchase." + STORE
OFFER = {"enabled": True, "monthly_cents": 199900, "markup_percent": 20, "hold_months": 3, "terms_url": ""}
STEPS = ["Payment confirmed", "Machine provisioned", "Address registered", "Service started and proved", "Node ready — sign-in sent"]


def order(state="launching", **more):
    return {"order_id": "nord_test", "state": state, "phase": "machine", "status": "working",
            "message": "Preparing your machine", "step": 5 if state in ("ready", "past_due") else 1 if state == "paid" else 2,
            "steps": STEPS, "offer": OFFER, "control_host": "must-not-compose.example",
            "open_url": "", "period_end": None, **more}


@pytest.fixture(scope="module", params=["chromium", "webkit"])
def browser(request):
    with sync_playwright() as pw:
        engine = getattr(pw, request.param).launch(headless=True)
        yield engine
        engine.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    context.add_cookies([{"name": "existing_backend_cookie", "value": "must-not-be-sent", "url": STORE}])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    yield page
    assert not errors, errors
    context.close()


def serve(page, *, offer=OFFER, offer_status=200, orders=None, post_answers=None, portal=None):
    state = {"requests": [], "posts": [], "polls": [], "portals": [], "external": []}
    orders = orders or [(200, order())]
    answers = post_answers or [(201, {"order_id": "nord_test", "checkout_url": "https://checkout.stripe.com/c/pay/test"})]

    def reply(route, status, body):
        if status == "abort":
            route.abort("connectionreset")
            return
        route.fulfill(status=status, content_type="application/json",
                      headers={"Access-Control-Allow-Origin": SITE, "Vary": "Origin"},
                      body=body if isinstance(body, str) else json.dumps(body))

    def handler(route):
        req = route.request
        if req.url.startswith(API):
            state["requests"].append(req)
            if req.method == "OPTIONS":
                route.fulfill(status=204, headers={"Access-Control-Allow-Origin": SITE,
                    "Access-Control-Allow-Methods": "GET, POST", "Access-Control-Allow-Headers": "Content-Type, Idempotency-Key"})
            elif req.url == API:
                reply(route, offer_status, offer)
            elif req.url == API + "/orders":
                state["posts"].append(req)
                reply(route, *answers[min(len(state["posts"]), len(answers)) - 1])
            elif req.url.endswith("/portal"):
                state["portals"].append(req)
                reply(route, *(portal or (200, {"portal_url": "https://billing.stripe.com/p/session/test"})))
            else:
                state["polls"].append(req)
                reply(route, *orders[min(len(state["polls"]), len(orders)) - 1])
        elif req.url.startswith("https://checkout.stripe.com"):
            # Playwright WebKit cannot fulfill a mocked navigation with 302.
            # This local Checkout stand-in returns the browser to the exact
            # configured success URL after the purchase click.
            target = SITE + "/sod/launching/?o=" + TOKEN + "&paid=1"
            route.fulfill(status=200, content_type="text/html", body="<script>location.replace(" + json.dumps(target) + ")</script>")
        elif urlsplit(req.url).netloc in {"cdnjs.cloudflare.com", "fonts.googleapis.com", "fonts.gstatic.com"}:
            # Exercise the sales page's existing static fallback without external requests.
            route.fulfill(status=200, content_type="text/javascript" if req.resource_type == "script" else "text/css", body="")
        elif urlsplit(req.url).netloc == "sneferu.ai":
            path = urlsplit(req.url).path
            file = ROOT / path.lstrip("/")
            if path.endswith("/"):
                file /= "index.html"
            if file.is_file():
                route.fulfill(path=str(file), content_type="image/svg+xml" if file.suffix == ".svg" else "text/html")
            else:
                route.fulfill(status=404)
        else:
            state["external"].append(req)
            route.fulfill(status=200, content_type="text/html", body="<h1>Destination fixture</h1>")

    page.route("**/*", handler)
    return state


def fill(page):
    page.locator("#name").fill("Ada Lovelace")
    page.locator("#email").fill("ada@example.test")


def no_overflow(page):
    size = page.evaluate("({viewport:innerWidth,width:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)})")
    assert size["width"] <= size["viewport"], size


def test_offer_uses_live_terms_and_button_above_fold(page):
    serve(page, offer={**OFFER, "monthly_cents": 212350, "markup_percent": 17, "hold_months": 6})
    page.goto(SITE + "/sod/signup/")
    expect(page.locator("#launchBtn")).to_be_enabled()
    expect(page.locator("#priceMonthly")).to_have_text("$2,123.50")
    expect(page.locator("#offerTerms")).to_contain_text("17%")
    expect(page.locator("#offerTerms")).to_contain_text("6 months")
    expect(page.locator("#launchBtn")).to_have_text("Launch your node — $2,123.50/month")
    no_overflow(page)
    box = page.locator("#launchBtn").bounding_box()
    assert box["y"] + box["height"] < 844, box


@pytest.mark.parametrize("status,offer", [(404,{}), (503,{}), (429,{}), (200,{**OFFER,"enabled":False}), (200,{**OFFER,"monthly_cents":None})])
def test_unavailable_or_invalid_offer_never_buys(page, status, offer):
    state = serve(page, offer=offer, offer_status=status)
    page.goto(SITE + "/sod/signup/")
    expect(page.locator("#retryOffer")).to_be_visible()
    expect(page.locator("#launchBtn")).to_be_disabled()
    fill(page)
    page.locator("#launchForm").evaluate("el => el.dispatchEvent(new Event('submit',{cancelable:true}))")
    assert state["posts"] == []
    no_overflow(page)


@pytest.mark.parametrize("path", ["/sod/signup/?left=1", "/sod/?left=1"])
def test_return_from_canceled_checkout_keeps_the_form(page, path):
    serve(page)
    saved = {"name": "Ada Lovelace", "email": "ada@example.test", "key": "node-order-preserved"}
    page.add_init_script("sessionStorage.setItem(" + json.dumps(ATTEMPT) + "," + json.dumps(json.dumps(saved)) + ");")
    page.goto(SITE + path)
    page.wait_for_url(SITE + "/sod/signup/?left=1")
    expect(page.locator("#launchMsg")).to_have_text("You left Checkout. Your place is kept; launch when ready.")
    expect(page.locator("#launchBtn")).to_be_enabled()
    expect(page.locator("#name")).to_have_value(saved["name"])
    expect(page.locator("#email")).to_have_value(saved["email"])


@pytest.mark.parametrize("viewport", [{"width": 1440, "height": 900}, {"width": 390, "height": 844}])
def test_sales_page_keeps_contact_and_opens_separate_signup(page, viewport):
    page.set_viewport_size(viewport)
    page.emulate_media(reduced_motion="reduce")
    state = serve(page)
    page.goto(SITE + "/sod/")
    expect(page.locator("#h1")).to_contain_text("What do you want to build?")
    expect(page.locator("#launchForm")).to_have_count(0)
    no_overflow(page)
    page.locator("#close-cta").click()
    expect(page.locator("#join")).to_be_visible()
    expect(page.locator("#join-title")).to_have_text("Contact us")
    page.keyboard.press("Escape")
    expect(page.locator("#join")).not_to_be_visible()
    assert state["requests"] == []
    page.locator(".cta-row").get_by_role("link", name="Join Now", exact=True).click()
    page.wait_for_url(SITE + "/sod/signup/")
    expect(page.locator("#launchForm")).to_be_visible()
    expect(page.locator("#launchBtn")).to_be_enabled()
    assert state["posts"] == []
    no_overflow(page)


def test_lost_checkout_response_reload_reuses_same_request(page):
    state = serve(page, post_answers=[("abort",{}), (202,{"detail":"Pending"})])
    page.goto(SITE + "/sod/signup/")
    fill(page)
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_contain_text("connection was interrupted")
    key = state["posts"][0].headers["idempotency-key"]
    page.reload()
    expect(page.locator("#name")).to_have_value("Ada Lovelace")
    expect(page.locator("#email")).to_have_value("ada@example.test")
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_contain_text("being checked")
    assert [r.headers["idempotency-key"] for r in state["posts"]] == [key, key]
    assert all("cookie" not in r.headers and "referer" not in r.headers for r in state["requests"])


@pytest.mark.parametrize("status,offer", [(200, {**OFFER, "enabled": False}), (404, {}), (503, {})])
def test_closed_offer_resumes_only_the_saved_purchase(page, status, offer):
    state = serve(page, offer=offer, offer_status=status,
                  post_answers=[(202, {"detail": "Pending"})])
    saved = {"name": "Ada Lovelace", "email": "ada@example.test", "key": "original-purchase"}
    page.add_init_script("sessionStorage.setItem(" + json.dumps(ATTEMPT) + "," + json.dumps(json.dumps(saved)) + ")")
    page.goto(SITE + "/sod/signup/?left=1")
    expect(page.locator("#launchBtn")).to_be_enabled()
    expect(page.locator("#launchBtn")).to_have_text("Resume saved checkout")
    # Changing the buyer cannot turn a saved retry into an unoffered purchase.
    page.locator("#email").fill("different@example.test")
    expect(page.locator("#launchBtn")).to_be_disabled()
    page.locator("#launchForm").evaluate("el => el.dispatchEvent(new Event('submit',{cancelable:true}))")
    assert not state["posts"]
    page.locator("#email").fill(saved["email"])
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_contain_text("being checked")
    assert len(state["posts"]) == 1
    assert state["posts"][0].headers["idempotency-key"] == saved["key"]
    assert state["posts"][0].post_data_json["email"] == saved["email"]
    no_overflow(page)


@pytest.mark.parametrize("status", [429, 503, 202])
def test_server_retry_keeps_checkout_identity(page, status):
    state = serve(page, post_answers=[(status,{"detail":"Retry"}), (202,{"detail":"Pending"})])
    page.goto(SITE + "/sod/signup/")
    fill(page)
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).not_to_have_text("Opening secure checkout…")
    if status == 503:
        expect(page.locator("#launchBtn")).to_be_disabled()
        page.locator("#retryOffer").click()
    else:
        expect(page.locator("#launchBtn")).to_be_enabled()
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_contain_text("being checked")
    assert len(state["posts"]) == 2
    assert state["posts"][0].headers["idempotency-key"] == state["posts"][1].headers["idempotency-key"]


def test_checkout_paid_phases_ready_then_billing_without_backend_navigation(page):
    state = serve(page, orders=[(200,order("paid")), (200,order(message="Registering your address",step=3,phase="dns")),
        (200,order("ready",message="Invitation sent",open_url="https://buyer.example/sod?from=receipt"))])
    page.clock.install()
    page.goto(SITE + "/sod/signup/")
    fill(page)
    page.locator("#launchBtn").click()
    page.wait_for_url(SITE + "/sod/launching/**")
    expect(page.locator("#lvKicker")).to_have_text("Payment received")
    with page.expect_request(API + "/orders/" + TOKEN):
        page.clock.fast_forward(5000)
    expect(page.locator("#lvMessage")).to_have_text("Registering your address")
    with page.expect_request(API + "/orders/" + TOKEN):
        page.clock.fast_forward(5000)
    expect(page.locator("#lvOpen")).to_be_visible()
    assert page.locator("#lvOpen").get_attribute("href") == "https://buyer.example/sod?from=receipt"
    expect(page.locator("#lvEmail")).to_have_text("We emailed your sign-in invitation to ada@example.test.")
    assert page.evaluate("key => sessionStorage.getItem(key)", ATTEMPT) is None
    no_overflow(page)
    page.locator("#lvPortal").click()
    page.wait_for_url("https://billing.stripe.com/**")
    assert len(state["portals"]) == 1
    assert all("cookie" not in r.headers and "referer" not in r.headers for r in state["requests"])


def test_ready_on_another_device_does_not_invent_email(page):
    serve(page, orders=[(200,order("ready", open_url="https://buyer.example/sod"))])
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvOpen")).to_be_visible()
    expect(page.locator("#lvEmail")).to_have_text("We emailed your sign-in invitation to the address you used at checkout.")
    assert "ada@example.test" not in page.locator("body").inner_text()


@pytest.mark.parametrize("bad", [(503,{}), (200,"<html>proxy response</html>"), (200,{"state":"unknown"})])
def test_poll_recovers_without_restarting_purchase(page, bad):
    state = serve(page, orders=[bad, (200,order("ready",open_url="https://buyer.example/sod"))])
    page.clock.install()
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvConnection")).to_contain_text("check again")
    page.clock.fast_forward(5000)
    expect(page.locator("#lvOpen")).to_be_visible()
    assert len(state["polls"]) == 2
    assert not state["posts"]


def test_stall_uses_launchers_words_and_keeps_polling(page):
    state = serve(page, orders=[(200,order(status="waiting",message="Waiting for cloud capacity. Retrying automatically."))])
    page.clock.install()
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvMessage")).to_have_text("Waiting for cloud capacity. Retrying automatically.")
    with page.expect_request(API + "/orders/" + TOKEN):
        page.clock.fast_forward(5000)
    expect(page.locator("#lvMessage")).to_have_text("Waiting for cloud capacity. Retrying automatically.")
    assert len(state["polls"]) >= 2
    assert "failed" not in page.locator("body").inner_text().lower()


def test_ready_without_address_never_composes_url_from_host(page):
    state = serve(page, orders=[(200,order("ready",open_url="javascript:alert(1)"))])
    page.clock.install()
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvMessage")).to_contain_text("checking its address")
    expect(page.locator("#lvOpen")).to_be_hidden()
    with page.expect_request(API + "/orders/" + TOKEN):
        page.clock.fast_forward(5000)
    expect(page.locator("#lvMessage")).to_contain_text("checking its address")
    # Wait for the request event after advancing the virtual clock.
    assert len(state["polls"]) >= 2


@pytest.mark.parametrize("token", ["", "short", "a/b?x=1"])
def test_invalid_token_never_calls_api(page, token):
    state = serve(page)
    page.goto(SITE + "/sod/launching/?o=" + token)
    expect(page.locator("#lvTitle")).to_have_text("This order link is incomplete.")
    assert not state["requests"]


def test_order_not_found_has_recovery_without_repurchase(page):
    state = serve(page, orders=[(404,{}),(200,order("paid"))])
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvTitle")).to_have_text("We couldn’t find that order.")
    expect(page.locator("#lvLede")).to_contain_text("Don’t purchase again")
    page.locator("#lvRetry").click()
    expect(page.locator("#lvKicker")).to_have_text("Payment received")
    assert not state["posts"]


def test_portal_error_keeps_ready_and_allows_retry(page):
    state = serve(page, orders=[(200,order("ready",open_url="https://buyer.example/sod"))],portal=(503,{}))
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvOpen")).to_be_visible()
    page.locator("#lvPortal").click()
    expect(page.locator("#lvBillingMessage")).to_contain_text("try again")
    page.locator("#lvPortal").click()
    expect(page.locator("#lvBillingMessage")).to_contain_text("try again")
    assert state["portals"][0].post_data_json["key"] == state["portals"][1].post_data_json["key"]
    expect(page.locator("#lvOpen")).to_be_visible()


def test_script_strings_are_only_text(page):
    serve(page, orders=[(200,order(message="<img src=x onerror=alert(1)>"))])
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvMessage")).to_have_text("<img src=x onerror=alert(1)>")
    assert page.locator("#lvMessage img").count() == 0


@pytest.mark.parametrize("width", [320, 390, 768, 1440])
def test_both_pages_fit_viewport(page, width):
    page.set_viewport_size({"width":width,"height":900})
    serve(page, orders=[(200,order("ready",open_url="https://buyer.example/sod"))])
    page.goto(SITE + "/sod/signup/")
    expect(page.locator("#launchBtn")).to_be_enabled()
    no_overflow(page)
    page.goto(SITE + "/sod/launching/?o=" + TOKEN)
    expect(page.locator("#lvOpen")).to_be_visible()
    no_overflow(page)


def test_promotion_code_retries_keep_one_purchase_identity(page):
    state = serve(page, post_answers=[(422, {"detail": "Promotion code unavailable"}),
                                      (202, {"detail": "Checking saved purchase"})])
    page.goto(SITE + "/sod/signup/")
    page.locator("#name").fill("Ada Lovelace")
    page.locator("#email").fill("ada@example.test")
    page.locator("#promotion").fill("invalid")
    expect(page.locator("#launchBtn")).to_have_text("Continue to Stripe")
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_have_text("Promotion code unavailable")
    page.locator("#promotion").fill("lifetime")
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_contain_text("being checked")
    assert [r.post_data_json["promotion_code"] for r in state["posts"]] == ["INVALID", "LIFETIME"]
    assert state["posts"][0].headers["idempotency-key"] == state["posts"][1].headers["idempotency-key"]


def test_closed_offer_restores_saved_promotion_and_refuses_edited_terms(page):
    page.add_init_script("sessionStorage.setItem(" + json.dumps(ATTEMPT) + "," + json.dumps(json.dumps({
        "name": "Ada Lovelace", "email": "ada@example.test", "promotion_code": "LIFETIME", "key": "saved-key"})) + ")")
    state = serve(page, offer_status=404, post_answers=[(202, {})])
    page.goto(SITE + "/sod/signup/")
    expect(page.locator("#promotion")).to_have_value("LIFETIME")
    expect(page.locator("#launchBtn")).to_be_enabled()
    page.locator("#promotion").fill("OTHER")
    expect(page.locator("#launchBtn")).to_be_disabled()
    page.locator("#promotion").fill("lifetime")
    page.locator("#launchBtn").click()
    expect(page.locator("#launchMsg")).to_contain_text("being checked")
    assert state["posts"][0].post_data_json["promotion_code"] == "LIFETIME"
