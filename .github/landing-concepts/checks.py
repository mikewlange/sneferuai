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


@pytest.mark.parametrize('width', [390, 1440])
@pytest.mark.parametrize('motion', ['no-preference', 'reduce'])
def test_sod_subscription_copy_preserves_story_without_money_scene(browser, site, width, motion):
    context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion=motion)
    page = context.new_page()
    state = intercept(page, site)
    try:
        page.goto(site + '/06-sod-subscription/?person=0')
        page.evaluate('document.fonts.ready')
        expect(page.locator('h1')).to_have_text('What do you want to build?')
        expect(page.locator('#prev-t2 h2')).to_have_text('Need changes or enhancements?Iterate until it’s perfect.')
        expect(page.locator('main')).to_have_count(1)
        assert page.locator('section.scene').evaluate_all('(scenes) => scenes.map(s => s.id)') == [
            's-ask', 's-tree', 's-build', 's-proof', 's-preview', 's-close']
        body = page.locator('body').inner_text().lower()
        for obsolete in ['pay for the work', 'invoice', '$38.20', '$60.00', 'estimates are never charged', 'join now']:
            assert obsolete not in body
        assert page.locator('[data-c^="delivery."]').count() == 0
        assert page.locator('meta[name="robots"]').get_attribute('content') == 'noindex,nofollow'
        if motion == 'no-preference':
            assert page.evaluate('!!window.gsap && !!window.ScrollTrigger')
            assert not page.evaluate('document.documentElement.classList.contains("static")')
            assert page.evaluate('ScrollTrigger.getAll().some(s => s.trigger.id === "s-preview")')
        else:
            assert page.evaluate('document.documentElement.classList.contains("static")')
        page.locator('#s-close').scroll_into_view_if_needed()
        expect(page.locator('#close-cta')).to_be_in_viewport()
        expect(page.locator('#s-close .cta-row')).to_have_css('opacity', '1')
        expect(page.locator('#s-close')).to_contain_text('by subscription')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not state['errors'], state
        assert not state['missing'], state
        assert not state['external'], state
        assert not state['posts']
    finally:
        context.close()


@pytest.mark.parametrize('button', ['hero-cta', 'bar-cta', 'close-cta'])
def test_sod_demo_requests_from_each_entry_point(browser, site, button):
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    state = intercept(page, site)
    try:
        page.goto(site + '/06-sod-subscription/?person=0')
        if button == 'bar-cta':
            page.evaluate('window.scrollTo(0, 250)')
            expect(page.locator('#bar')).to_have_class('bar on')
        elif button == 'close-cta':
            page.locator('#s-close').scroll_into_view_if_needed()
        page.locator('#' + button).click()
        expect(page.locator('#join')).to_be_visible()
        expect(page.locator('#join-title')).to_have_text('See it for yourself.')
        page.locator('#join-name').fill('Preview Visitor')
        page.locator('#join-email').fill('preview@example.test')
        page.locator('#join-submit').click()
        expect(page.locator('#join-form-status')).to_contain_text('Thanks.')
        assert len(state['posts']) == 1
        assert 'Software On Demand demo request' in state['posts'][0].post_data
        page.locator('#join-done').click()
        expect(page.locator('#join')).not_to_be_visible()
        assert not state['errors'], state
        assert not state['external'], state
    finally:
        context.close()


def test_sod_story_and_demo_survive_animation_library_failure(browser, site):
    context = browser.new_context(viewport={'width': 390, 'height': 844})
    page = context.new_page()
    state = intercept(page, site)
    page.route('**/vendor/*.js', lambda route: route.fulfill(content_type='application/javascript', body=''))
    try:
        page.goto(site + '/06-sod-subscription/')
        assert page.evaluate('document.documentElement.classList.contains("static")')
        expect(page.locator('#hero-cta')).to_be_visible()
        page.locator('#hero-cta').click()
        expect(page.locator('#join')).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator('#join')).not_to_be_visible()
        page.locator('#s-close').scroll_into_view_if_needed()
        expect(page.locator('#close-cta')).to_be_in_viewport()
        assert not state['errors'], state
    finally:
        context.close()


@pytest.mark.parametrize('width', [390, 1440])
def test_sod_composer_keeps_original_rectangle_through_scroll_and_refresh(browser, site, width):
    context = browser.new_context(viewport={'width': width, 'height': 900})
    page = context.new_page()
    state = intercept(page, site)

    def scroll_to_time(time):
        page.evaluate('''time => {
            const scene = ScrollTrigger.getAll().find(s => s.trigger.id === 's-ask');
            window.scrollTo(0, scene.start + time / scene.animation.duration() * (scene.end - scene.start));
            ScrollTrigger.update();
        }''', time)
        page.wait_for_function('''time => Math.abs(
            ScrollTrigger.getAll().find(s => s.trigger.id === 's-ask').animation.time() - time
        ) < .02''', arg=time)
        expect(page.locator('#composer')).to_have_css('border-radius', '26px')

    try:
        page.goto(site + '/06-sod-subscription/?person=0')
        page.evaluate('document.fonts.ready')
        # Both typing examples, the departure, and scrolling back from the idea scene.
        for time in [4, 9, 11, 18, 9, 4]:
            scroll_to_time(time)
        scroll_to_time(18)
        page.set_viewport_size({'width': 768, 'height': 900})
        page.evaluate('ScrollTrigger.refresh()')
        scroll_to_time(9)
        expect(page.locator('#composer')).to_have_css('opacity', '1')
        scroll_to_time(18)
        page.reload()
        page.evaluate('document.fonts.ready')
        scroll_to_time(4)
        expect(page.locator('#composer')).to_have_css('opacity', '1')
        assert not state['errors'], state
        assert not state['missing'], state
    finally:
        context.close()
