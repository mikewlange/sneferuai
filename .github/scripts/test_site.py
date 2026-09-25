"""Run with python3 -m unittest discover -s .github/scripts -p 'test_*.py'."""
from html.parser import HTMLParser
from hashlib import sha256
import re
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

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
        self.assertEqual(set(dialogs), {'life-dialog', 'restoration-dialog', 'flow-dialog', 'esm-dialog', 'fdc-dialog'})
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
                    self.assertEqual(urlsplit(attrs.get('src', '')).path, 'v2/assets/site.js')

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

    def test_root_keeps_the_selected_design_with_shared_assets(self):
        # The root is now the editing surface; /v2 is a retained design copy.
        # Protect the shared design without forcing independent copy edits to match.
        for page in ['index.html', 'system.html']:
            nodes = Elements((ROOT / page).read_text(encoding='utf-8')).nodes
            self.assertEqual(sum(tag == 'main' and attrs.get('id') == 'main' for tag, attrs in nodes), 1)
            self.assertTrue(any(attrs.get('id') == 'site-nav' for _, attrs in nodes))
            self.assertEqual([urlsplit(attrs['href']).path for tag, attrs in nodes
                              if tag == 'link' and attrs.get('rel') == 'stylesheet'
                              and not urlsplit(attrs['href']).netloc], ['v2/assets/site.css'])
        self.assertTrue({'top', 'platform', 'finishes', 'on-demand', 'origin', 'work', 'faq', 'contact'}
                        <= {attrs.get('id') for tag, attrs in self.home if tag == 'section'})

    def test_self_improvement_features_esm_and_fdc_not_the_game(self):
        source = (ROOT / 'index.html').read_text(encoding='utf-8')
        work = re.search(r'<section[^>]*id="work".*?</section>', source, re.S).group()
        work_nodes = Elements(work).nodes
        targets = {attrs['data-dialog'] for _, attrs in work_nodes if 'data-dialog' in attrs}
        self.assertEqual(targets, {'esm-dialog', 'fdc-dialog'})
        self.assertIn('05 / Built with Sneferu for Sneferu', work)
        self.assertIn('Self-improvement.', work)
        self.assertTrue(any(tag == 'img' and attrs.get('src') == 'v2/assets/shots/fdc-overview.webp'
                            for tag, attrs in work_nodes))
        ticker = re.search(r'<ul class="ticker-track">.*?</ul>', source, re.S).group()
        self.assertIn('https://github.com/sneferu-ai/hungerhall', ticker)

    def test_fdc_demo_retains_screenshots_and_simulation_boundary(self):
        source = (ROOT / 'index.html').read_text(encoding='utf-8')
        dialog = re.search(r'<dialog[^>]*id="fdc-dialog".*?</dialog>', source, re.S).group()
        nodes = Elements(dialog).nodes
        for shot in ['fdc-bloom.webp', 'fdc-overview.webp', 'fdc-audit.webp']:
            self.assertTrue(any(tag == 'img' and attrs.get('src') == f'v2/assets/shots/{shot}'
                                for tag, attrs in nodes), shot)
            self.assertTrue((ROOT / 'v2/assets/shots' / shot).is_file())
        self.assertIn('simulated model responses', dialog)
        self.assertIn('not a completed production fine-tune', dialog)
        self.assertIn('120-item test', dialog)
        self.assertIn('36 traceable training examples', dialog)

    def test_shared_scripts_and_styles_have_current_cache_versions(self):
        for prefix in ['', 'v2/']:
            for page in ['index.html', 'system.html']:
                directory = ROOT / prefix
                nodes = Elements((directory / page).read_text(encoding='utf-8')).nodes
                for tag, attrs in nodes:
                    reference = attrs.get('src') if tag == 'script' else attrs.get('href') if attrs.get('rel') == 'stylesheet' else None
                    if not reference or urlsplit(reference).netloc:
                        continue
                    url = urlsplit(reference)
                    digest = sha256((directory / url.path).read_bytes()).hexdigest()[:12]
                    self.assertEqual(parse_qs(url.query).get('v'), [digest])

    def test_new_pages_do_not_link_to_original_homepage(self):
        for prefix in ['', 'v2/']:
            for page in ['index.html', 'system.html']:
                nodes = Elements((ROOT / prefix / page).read_text(encoding='utf-8')).nodes
                self.assertFalse(any('field-notes.html' in attrs.get('href', '') for tag, attrs in nodes if tag == 'a'))
        # Retain the existing archive, without adding it to the new navigation.
        archive = (ROOT / 'field-notes.html').read_text(encoding='utf-8')
        self.assertIn('Archived system field notes and recorded builds.', archive)


if __name__ == '__main__':
    main()
