"""Safety tests for GeoSite conversion without overmatching."""
import tempfile
import unittest
from pathlib import Path
from scripts.convert import collect, convert, equivalent_suffix, is_covered

class ConverterTests(unittest.TestCase):
    def test_suffix_equivalent_regex(self):
        self.assertEqual(equivalent_suffix(r"^(?:.*\.)?example\.com$"), "example.com")
        self.assertIsNone(equivalent_suffix(r"^sub\.example\.com$"))
        self.assertIsNone(equivalent_suffix(r"^.*example\.com$"))

    def test_exact_not_widened(self):
        rules, covered, converted, unsupported = convert({
            ("full", "stun1.example.com", "test", 1),
        })
        self.assertEqual(rules, set())
        self.assertEqual(len(unsupported), 1)
        self.assertEqual(len(covered), 0)

    def test_exact_covered_by_existing_suffix(self):
        rules, covered, converted, unsupported = convert({
            ("full", "a.example.com", "test", 1),
            ("domain", "example.com", "test", 2),
        })
        self.assertEqual(rules, {(2, "example.com")})
        self.assertEqual(len(covered), 1)
        self.assertEqual(unsupported, [])

    def test_keyword_coverage(self):
        self.assertTrue(is_covered("mail.example.com", {(3, "example")}))
        self.assertFalse(is_covered("notexample.net", {(2, "example.net")}))

    def test_filter_include(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "child").write_text("domain:yes.example @cn\ndomain:no.example\n")
            (root / "parent").write_text("include:child @cn\n")
            records = collect("parent", root)
            self.assertIn(("domain", "yes.example", "child", 1), records)
            self.assertNotIn(("domain", "no.example", "child", 2), records)

if __name__ == "__main__":
    unittest.main()
