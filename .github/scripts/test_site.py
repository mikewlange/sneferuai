"""Run with python3 -m unittest discover -s .github/scripts -p 'test_*.py'."""
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
                    self.assertEqual(attrs.get('src'), '/assets/site.js')

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


if __name__ == '__main__':
    main()
