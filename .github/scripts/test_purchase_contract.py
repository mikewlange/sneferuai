"""Publication checks for the public-site purchase pages; no network calls."""
from pathlib import Path
import re
from unittest import TestCase

from test_site import Elements

ROOT = Path(__file__).resolve().parents[2]
PAGES = ("sod/index.html", "sod/launching/index.html")


class PurchaseContractTests(TestCase):
    def test_no_third_party_scripts_or_token_referrer(self):
        origins = []
        for path in PAGES:
            text = (ROOT / path).read_text()
            nodes = Elements(text).nodes
            self.assertEqual(sum(tag == "script" for tag, _ in nodes), 1)
            self.assertFalse(any(tag == "script" and attrs.get("src") for tag, attrs in nodes))
            self.assertTrue(any(tag == "meta" and attrs.get("name") == "referrer" and attrs.get("content") == "no-referrer" for tag, attrs in nodes))
            origins.append(re.findall(r'const STORE_ORIGIN = "(https://[^/\"]+)";', text))
            self.assertNotIn("formspree", text.lower())
            self.assertIn('credentials:"omit"', text)
        self.assertEqual(len(origins[0]), 1)
        self.assertEqual(origins[0], origins[1])

    def test_price_is_loaded_and_buying_starts_disabled(self):
        text = (ROOT / PAGES[0]).read_text()
        nodes = Elements(text).nodes
        button = next(attrs for tag, attrs in nodes if attrs.get("id") == "launchBtn")
        self.assertIn("disabled", button)
        self.assertNotRegex(text, r'\$1,?999|199900')
        self.assertIn('"Idempotency-Key":attempt.key', text)

    def test_missing_order_is_not_a_new_purchase(self):
        nodes = Elements((ROOT / PAGES[1]).read_text()).nodes
        self.assertFalse(any(tag == "form" for tag, _ in nodes))
        self.assertTrue(any(tag == "meta" and attrs.get("name") == "robots" and attrs.get("content") == "noindex, nofollow" for tag, attrs in nodes))
