"""Real browsers, local draft pages, intercepted demo submissions only."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent
SLUGS = ['01-limestone', '02-night', '03-copper', '04-short-story', '05-in-your-hands']
FORM = 'https://formspree.io/f/xpqvqqra'


@pytest.fixture(scope='module')
def site():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield 'http://127.0.0.1:' + str(server.server_port)
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture(scope='module', params=['chromium', 'webkit'])
def browser(request):
    with sync_playwright() as pw:
        instance = getattr(pw, request.param).launch()
        yield instance
        instance.close()


def intercept(page, site, *, fail_first=False):
    state = {'posts': [], 'external': [], 'missing': [], 'errors': []}
    page.on('pageerror', lambda error: state['errors'].append(str(error)))
    page.on('response', lambda response: state['missing'].append(response.url)
            if response.url.startswith(site) and response.status >= 400 else None)

    def route(request):
        if request.request.url == FORM:
            state['posts'].append(request.request)
            if fail_first and len(state['posts']) == 1:
                request.abort('connectionreset')
            else:
                request.fulfill(status=200, content_type='application/json',
                                headers={'Access-Control-Allow-Origin': '*'}, body='{"ok":true}')
        elif request.request.url.startswith(site + '/'):
            request.continue_()
        else:
            state['external'].append(request.request.url)
            request.abort()
    page.route('**/*', route)
    return state


@pytest.mark.parametrize('slug', SLUGS)
def test_layout_assets_and_demo_request(browser, site, slug):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    page = context.new_page()
    state = intercept(page, site)
    try:
        assert page.goto(site + '/' + slug + '/').status == 200
        page.evaluate('document.fonts.ready')
        expect(page.locator('h1')).to_have_count(1)
        assert 30 <= len(page.locator('main').inner_text().split()) <= 130
        assert 'autonomous' in page.locator('main').inner_text().lower()
        assert page.locator('img').evaluate_all('(images) => images.every(i => i.complete && i.naturalWidth > 0)')
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({'width': width, 'height': 900})
            dimensions = page.evaluate('({viewport: innerWidth, width: document.documentElement.scrollWidth})')
            assert dimensions['width'] <= dimensions['viewport'], (slug, dimensions)
        opener = page.locator('[data-demo]').first
        opener.click()
        expect(page.locator('#demo')).to_be_visible()
        page.locator('input[name="name"]').fill('Preview Visitor')
        page.locator('input[name="email"]').fill('preview@example.test')
        page.locator('button[type="submit"]').click()
        expect(page.locator('[role="status"]')).to_contain_text('Thanks.')
        expect(page.locator('#demo form')).to_be_hidden()
        assert len(state['posts']) == 1
        assert state['posts'][0].method == 'POST'
        assert 'preview@example.test' in state['posts'][0].post_data
        page.locator('[data-close]').click()
        expect(page.locator('#demo')).not_to_be_visible()
        expect(opener).to_be_focused()
        assert not state['external'], state
        assert not state['missing'], state
        assert not state['errors'], state
    finally:
        context.close()


@pytest.mark.parametrize('slug', SLUGS)
def test_copy_and_contact_survive_without_javascript(browser, site, slug):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    state = intercept(page, site)
    try:
        page.goto(site + '/' + slug + '/')
        expect(page.locator('h1')).to_be_visible()
        assert all(link.startswith('mailto:mike@sneferu.ai')
                   for link in page.locator('[data-demo]').evaluate_all('(links) => links.map(l => l.href)'))
        assert len(page.locator('main').inner_text().split()) >= 30
        assert not state['posts']
        assert not state['external']
        assert not state['missing']
    finally:
        context.close()


def test_failed_demo_request_retains_input_and_can_retry(browser, site):
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    state = intercept(page, site, fail_first=True)
    try:
        page.goto(site + '/01-limestone/')
        page.locator('[data-demo]').first.click()
        page.keyboard.press('Escape')
        expect(page.locator('#demo')).not_to_be_visible()
        page.locator('[data-demo]').first.click()
        page.locator('input[name="name"]').fill('Preview Visitor')
        page.locator('input[name="email"]').fill('preview@example.test')
        page.locator('button[type="submit"]').click()
        expect(page.locator('[role="status"]')).to_contain_text('didn’t go through')
        expect(page.locator('input[name="email"]')).to_have_value('preview@example.test')
        expect(page.locator('button[type="submit"]')).to_be_enabled()
        page.locator('button[type="submit"]').click()
        expect(page.locator('[role="status"]')).to_contain_text('Thanks.')
        assert len(state['posts']) == 2
        assert not state['errors']
    finally:
        context.close()


def test_scroll_chapters_and_reduced_motion(browser, site):
    context = browser.new_context(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
    page = context.new_page()
    state = intercept(page, site)
    try:
        page.goto(site + '/04-short-story/')
        page.locator('[data-chapter="1"]').scroll_into_view_if_needed()
        expect(page.locator('[data-stage-name]')).to_have_text('The build')
        expect(page.locator('[data-art-layer="1"]')).to_have_class('active')
        page.locator('[data-chapter="2"]').scroll_into_view_if_needed()
        expect(page.locator('[data-stage-name]')).to_have_text('Your software')
        expect(page.locator('[data-art-layer="2"]')).to_have_class('active')
        assert page.locator('html').evaluate('el => getComputedStyle(el).scrollBehavior') == 'auto'
        page.goto(site + '/05-in-your-hands/')
        page.locator('footer').scroll_into_view_if_needed()
        expect(page.locator('.progress')).to_have_css('transform', 'matrix(1, 0, 0, 1, 0, 0)')
        assert not state['errors']
        assert not state['missing']
    finally:
        context.close()


def test_gallery_opens_all_five_designs(browser, site):
    context = browser.new_context()
    page = context.new_page()
    state = intercept(page, site)
    try:
        page.goto(site + '/')
        expect(page.locator('.concept')).to_have_count(5)
        for index, slug in enumerate(SLUGS):
            page.locator('.concept .open').nth(index).click()
            expect(page).to_have_url(site + '/' + slug + '/')
            page.go_back()
        page.locator('footer').scroll_into_view_if_needed()
        assert page.locator('img').evaluate_all('(images) => images.every(i => i.complete && i.naturalWidth > 0)')
        for width in [320, 390, 768, 1440]:
            page.set_viewport_size({'width': width, 'height': 900})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not state['errors']
        assert not state['missing']
    finally:
        context.close()
