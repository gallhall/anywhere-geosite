"""Tests for affiliation-aware GeoSite conversion and fail-safe publishing."""
import tempfile
import unittest
from pathlib import Path

from scripts.convert import (
    DomainLists, convert, equivalent_suffix, is_covered,
    previous_rule_count, conflict_report,
)


class ConverterTests(unittest.TestCase):
    def test_equivalent_regex(self):
        self.assertEqual(equivalent_suffix(r"^(?:.*\.)?example\.com$"), "example.com")
        self.assertIsNone(equivalent_suffix(r"^sub\.example\.com$"))
        self.assertIsNone(equivalent_suffix(r"^.*example\.com$"))

    def test_exact_stays_exact(self):
        rules, covered, _, unsupported = convert({
            ("full", "stun1.example.com", (), "test", 1)
        })
        self.assertEqual(rules, set())
        self.assertEqual(len(unsupported), 1)
        self.assertEqual(len(covered), 0)

    def test_exact_already_covered(self):
        rules, covered, _, unsupported = convert({
            ("full", "a.example.com", (), "test", 1),
            ("domain", "example.com", (), "test", 2),
        })
        self.assertEqual(rules, {(2, "example.com")})
        self.assertEqual(len(covered), 1)
        self.assertEqual(unsupported, [])

    def test_keywords(self):
        self.assertTrue(is_covered("mail.example.com", {(3, "example")}))
        self.assertFalse(is_covered("notexample.net", {(2, "example.net")}))

    def test_affiliations_and_filtered_includes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "child").write_text(
                "domain:yes.example @cn &alias\n"
                "domain:no.example &alias\n"
                "full:ads.example @ads &virtual\n",
                encoding="utf-8",
            )
            (root / "parent").write_text("include:child @cn @-ads\n", encoding="utf-8")
            db = DomainLists(root)
            self.assertEqual({r[1] for r in db.select("parent")}, {"yes.example"})
            self.assertEqual({r[1] for r in db.select("alias")},
                             {"yes.example", "no.example"})
            self.assertEqual({r[1] for r in db.select("virtual")}, {"ads.example"})
            self.assertEqual({r[1] for r in db.select("child@ads")}, {"ads.example"})

    def test_include_chain_and_virtual_affiliations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("include:virtual @cn\n", encoding="utf-8")
            (root / "b").write_text("domain:abc.example @cn &virtual\n", encoding="utf-8")
            self.assertEqual({r[1] for r in DomainLists(root).select("a")},
                             {"abc.example"})

    def test_cyclic_include(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("include:b\n", encoding="utf-8")
            (root / "b").write_text("include:a\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                DomainLists(root).select("a")

    def test_drop_guard_input(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "rules.arrs"
            file.write_text("name = test\n2, example.com\n3, ad\n")
            self.assertEqual(previous_rule_count(file), 2)

    def test_conflict_detector(self):
        report = conflict_report({
            "ads": {(2, "ads.example.com"), (2, "same.example")},
            "cn": {(2, "example.com"), (2, "same.example")},
        })
        self.assertEqual(report["identical_count"], 1)
        self.assertEqual(report["suffix_overlap_count"], 1)


if __name__ == "__main__":
    unittest.main()
