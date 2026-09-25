"""Run with python3 -m unittest discover -s .github/scripts -p 'test_*.py'."""
import re
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch

import build_site

ROOT = Path(__file__).resolve().parents[2]


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.nodes = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


class PublicInputTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve()
        (self.repo / 'index.html').write_text('public', encoding='utf-8')
        (self.repo / 'system.html').write_text('new public', encoding='utf-8')
        (self.repo / 'private.docx').write_bytes(b'not for publication')
        mocked = patch.object(build_site, 'tracked_files', return_value=[PurePosixPath('index.html')])
        mocked.start()
        self.addCleanup(mocked.stop)

    def test_untracked_documents_are_not_discovered(self):
        self.assertEqual(build_site.publish_inputs(self.repo, []), [PurePosixPath('index.html')])

    def test_explicit_public_file_is_deduplicated(self):
        self.assertEqual(build_site.publish_inputs(self.repo, ['system.html', 'system.html']),
                         [PurePosixPath('index.html'), PurePosixPath('system.html')])

    def test_unsafe_paths_rejected(self):
        for value in ['', '.', '/tmp/a', '../a', 'assets/../a', '.env', '.github/a', '_site/index.html']:
            with self.subTest(value=value), self.assertRaises(SystemExit):
                build_site.publish_inputs(self.repo, [value])

    def test_missing_file_rejected(self):
        with self.assertRaises(SystemExit):
            build_site.publish_inputs(self.repo, ['missing.html'])

    def test_direct_symlink_rejected(self):
        (self.repo / 'alias.html').symlink_to(self.repo / 'index.html')
        with self.assertRaises(SystemExit):
            build_site.publish_inputs(self.repo, ['alias.html'])

    def test_parent_symlink_outside_repo_rejected(self):
        with TemporaryDirectory() as outside:
            (Path(outside) / 'file.html').write_text('private', encoding='utf-8')
            (self.repo / 'outside').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(SystemExit):
                build_site.publish_inputs(self.repo, ['outside/file.html'])


class OverviewTests(TestCase):
    def setUp(self):
        self.home = Elements((ROOT / 'index.html').read_text(encoding='utf-8')).nodes

    def test_tab_panel_relationships_and_initial_state(self):
        tabs = [attrs for _, attrs in self.home if attrs.get('role') == 'tab']
        panels = {attrs['id']: attrs for _, attrs in self.home if attrs.get('role') == 'tabpanel'}
        self.assertEqual(len(tabs), 4)
        self.assertEqual(sum(tab.get('aria-selected') == 'true' for tab in tabs), 1)
        for tab in tabs:
            panel = panels[tab['aria-controls']]
            self.assertEqual(panel['aria-labelledby'], tab['id'])
            self.assertEqual('hidden' in panel, tab['aria-selected'] == 'false')
            self.assertEqual(tab['tabindex'], '0' if tab['aria-selected'] == 'true' else '-1')

    def test_case_buttons_have_named_dialogs(self):
        dialogs = {a['id']: a for tag, a in self.home if tag == 'dialog'}
        ids = {a['id'] for _, a in self.home if 'id' in a}
        self.assertEqual(set(dialogs), {'life-dialog', 'restoration-dialog', 'flow-dialog', 'esm-dialog', 'hunger-dialog'})
        for _, attrs in self.home:
            if 'data-dialog' in attrs:
                self.assertIn(attrs['data-dialog'], dialogs)
        for dialog in dialogs.values():
            self.assertIn(dialog['aria-labelledby'], ids)

    def test_image_alternatives_and_local_interactions(self):
        for page in ['index.html', 'system.html']:
            nodes = Elements((ROOT / page).read_text(encoding='utf-8')).nodes
            self.assertEqual(sum(tag == 'h1' for tag, _ in nodes), 1)
            for tag, attrs in nodes:
                if tag == 'img':
                    self.assertTrue(attrs.get('alt'))
                if tag == 'script':
                    # document-relative on purpose: the same files serve at /v2/ (preview) and at the root (live)
                    self.assertEqual(attrs.get('src'), 'assets/site.js')

    def test_existing_contact_destination_preserved(self):
        forms = [attrs for tag, attrs in self.home if tag == 'form']
        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0]['action'], 'https://formspree.io/f/xpqvqqra')
        self.assertEqual(forms[0]['method'], 'post')

    def test_motion_control_on_both_pages_and_no_video_autoplay(self):
        for page in ['index.html', 'system.html']:
            nodes = Elements((ROOT / page).read_text(encoding='utf-8')).nodes
            controls = [a for tag, a in nodes if tag == 'button' and a.get('class') == 'motion-toggle']
            self.assertEqual(len(controls), 1)
            self.assertEqual(controls[0]['aria-label'], 'Pause decorative motion')
            for tag, attrs in nodes:
                if tag == 'video':
                    self.assertNotIn('autoplay', attrs)


class Text(HTMLParser):
    """Visible text of a page, so copy rules are checked against what a reader sees."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    @property
    def text(self):
        return ' '.join(' '.join(self.parts).split())


PUBLIC_PAGES = ['index.html', 'system.html']

# One public name per thing. The site, the product, and the Atlas agree on these.
CONSTANT_NAMES = ['Sneferu', 'Snef', 'Sneferu Coders', 'Idea Bloom', 'Research Expedition', 'Game Autopilot',
                  'Business Autopilot', 'Goal Master', 'Problem Solver', 'Demo Studio', 'Spec Factory',
                  'Software On Demand', 'ESM', 'Run Truth', 'adversarial convergence']
# Retired or duplicate names that must not reappear on the public site.
RETIRED_NAMES = ['Game Studio', 'Business Studio', 'Build-a-Business', 'Build a business', 'Build a Business',
                 'ESM-Gateway', 'Game production', 'Ideate → Pick → Build', 'Software Factory']
# From the proof-points sheet: claims the site never makes.
DO_NOT_SAY = ['zero humans', 'guaranteed', "can't be wrong", 'cannot be wrong', 'never fails', 'shipped game',
              'made a discovery', 'enterprise-ready', 'build anything', 'the best AI', 'the best system',
              # Bent Pyramid doc §5: contested Egyptology that a scientific reader will catch.
              'meidum collapsed', 'pyramid collapsed', '54°27', '43°22', 'buried in the red pyramid', 'first true pyramid.']


class NamingTests(TestCase):
    def setUp(self):
        self.pages = {page: Text((ROOT / page).read_text(encoding='utf-8')).text for page in PUBLIC_PAGES}

    def test_constant_names_appear_on_the_public_pages(self):
        everywhere = ' '.join(self.pages.values())
        for name in CONSTANT_NAMES:
            self.assertIn(name, everywhere, name)
        for name in ['Snef', 'Sneferu Coders', 'Idea Bloom', 'Research Expedition', 'Game Autopilot',
                     'Business Autopilot', 'Software On Demand', 'ESM']:
            self.assertIn(name, self.pages['index.html'], f'homepage must name {name}')
        # the engine's name (adversarial convergence) lives on the Inside Sneferu page; the homepage
        # no longer has an engine section (2026-09-24), so it is checked in CONSTANT_NAMES across pages only

    def test_retired_names_do_not_reappear(self):
        for page, text in self.pages.items():
            for name in RETIRED_NAMES:
                self.assertNotIn(name, text, f'{page} uses retired name {name!r}')

    def test_sneferu_brain_is_only_used_to_introduce_snef(self):
        for page, text in self.pages.items():
            for match in re.finditer('Sneferu Brain', text):
                lead = text[max(0, match.start() - 16):match.start()]
                self.assertIn('Snef', lead, f'{page}: "Sneferu Brain" must follow "Snef" ({lead!r})')

    def test_no_em_or_en_dashes_in_public_copy(self):
        # House style: nothing that is not on a keyboard.
        for page in PUBLIC_PAGES:
            source = (ROOT / page).read_text(encoding='utf-8')
            for dash in ('\u2014', '\u2013'):
                self.assertNotIn(dash, source, f'{page} contains {dash!r}')

    def test_claims_the_site_never_makes(self):
        for page, text in self.pages.items():
            lowered = text.lower()
            for phrase in DO_NOT_SAY:
                self.assertNotIn(phrase.lower(), lowered, f'{page} says {phrase!r}')


class RunPanelTests(TestCase):
    def setUp(self):
        self.home = Elements((ROOT / 'index.html').read_text(encoding='utf-8')).nodes

    def test_one_run_has_five_scenes_with_status_lines(self):
        scenes = [attrs for _, attrs in self.home if 'data-scene' in attrs]
        self.assertEqual([attrs['data-scene'] for attrs in scenes], ['0', '1', '2', '3', '4'])
        for attrs in scenes:
            self.assertTrue(attrs.get('data-status'))
        self.assertEqual(sum('data-run' in attrs for _, attrs in self.home), 1)
        self.assertEqual(sum('data-run-state' in attrs for _, attrs in self.home), 1)
        self.assertEqual(sum('data-run-type' in attrs for _, attrs in self.home), 1)
        self.assertEqual(sum('data-run-replay' in attrs for _, attrs in self.home), 1)

    def test_run_panel_is_labelled_as_an_illustration(self):
        text = Text((ROOT / 'index.html').read_text(encoding='utf-8')).text
        self.assertIn('An illustration, not a live feed', text)


class TickerTests(TestCase):
    """The strip under the hero shows the finished products' logos; each one links to its repository."""

    def _items(self):
        source = (ROOT / 'index.html').read_text(encoding='utf-8')
        track = re.search(r'<ul class="ticker-track">(.*?)</ul>', source, re.S).group(1)
        return re.findall(r'<li class="logo logo-([a-z-]+)"><a href="([^"]+)"([^>]*)><img src="([^"]+)" alt="([^"]*)"', track)

    def test_every_logo_links_to_its_repository_or_to_software_on_demand(self):
        items = self._items()
        self.assertGreaterEqual(len(items), 10)
        for name, href, attrs, src, alt in items:
            self.assertEqual(src, f'assets/logos/{name}.png', name)
            self.assertTrue((ROOT / src.lstrip('/')).is_file(), src)
            self.assertTrue(alt.strip(), f'{name} has no alt text')
            if name == 'software-on-demand':
                self.assertEqual(href, 'sod/')
                self.assertNotIn('target=', attrs, 'the SOD page opens in the same tab')
            else:
                self.assertRegex(href, r'^https://github\.com/sneferu-ai/[a-z0-9-]+$', name)
                self.assertIn('target="_blank"', attrs, name)
                self.assertIn('rel="noopener"', attrs, name)

    def test_every_logo_tile_has_its_own_background_colour(self):
        css = (ROOT / 'assets' / 'site.css').read_text(encoding='utf-8')
        for name, *_ in self._items():
            self.assertRegex(css, rf'\.logo-{name}\{{--tile:#[0-9a-fA-F]{{3,6}}\}}', name)

    def test_the_strip_no_longer_carries_text_items(self):
        source = (ROOT / 'index.html').read_text(encoding='utf-8')
        track = re.search(r'<ul class="ticker-track">(.*?)</ul>', source, re.S).group(1)
        self.assertNotIn('<li><b>', track)


class SystemPageTests(TestCase):
    def test_tour_index_points_at_parts_on_the_page(self):
        source = (ROOT / 'system.html').read_text(encoding='utf-8')
        nodes = Elements(source).nodes
        ids = {attrs['id'] for _, attrs in nodes if 'id' in attrs}
        index = re.search(r'<nav class="tour-index"[^>]*>(.*?)</nav>', source, re.S).group(1)
        targets = re.findall(r'href="#([a-z-]+)"', index)
        self.assertGreaterEqual(len(targets), 8)
        for target in targets:
            self.assertIn(target, ids)
        names = [attrs for tag, attrs in nodes if tag == 'span' and attrs.get('class') == 'part-name']
        self.assertGreaterEqual(len(names), 8)


if __name__ == '__main__':
    main()
