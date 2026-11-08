#!/usr/bin/env python3
"""Compile selected domain-list-community categories into Anywhere rules.

The source parser supports include filters, @attributes and &affiliations.
Anywhere cannot represent exact-only or arbitrary regexp matches. Unsafe
approximations are reported, never inserted as suffix rules.
"""
import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

TARGETS = {
    "force-proxy": (["google", "microsoft", "oracle"], 0),
    "cn": (["cn"], 1),
    "private": (["private"], 1),
    "steam-cn": (["steam@cn"], 1),
    "ads": (["category-ads-all"], 2),
    "stun": (["category-stun"], 2),
}
SAFE_SUFFIX_REGEX = re.compile(
    r"^\^\(\?:\.\*\\\.\)\?((?:[a-z0-9-]+\\\.)+[a-z0-9-]+)\$$", re.I)
VALID_HOST = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$", re.I)


def equivalent_suffix(regex):
    """Only anchored optional-subdomain + literal-domain regexes are equivalent."""
    match = SAFE_SUFFIX_REGEX.fullmatch(regex)
    if not match:
        return None
    host = match.group(1).replace(r"\.", ".").lower()
    return host if VALID_HOST.fullmatch(host) else None


def matches_filters(attrs, selectors):
    return all((selector[1:] not in attrs if selector.startswith("-")
                else selector in attrs) for selector in selectors)


class DomainLists:
    def __init__(self, root):
        self.root = Path(root)
        self.files = {}
        self.affiliations = defaultdict(set)
        self.cache = {}
        for path in sorted(self.root.iterdir()):
            if not path.is_file() or path.name.startswith("."):
                continue
            entries = []
            for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                value = raw.split("#", 1)[0].strip()
                if not value:
                    continue
                parts = value.split()
                kind, colon, domain = parts[0].partition(":")
                if not colon:
                    kind, domain = "domain", kind
                if kind == "include":
                    selectors = tuple(x[1:].lower() for x in parts[1:] if x.startswith("@"))
                    if any(not x.startswith("@") for x in parts[1:]):
                        raise ValueError(f"Invalid include modifiers: {path.name}:{number}")
                    entries.append(("include", domain.lower(), selectors))
                    continue
                attrs = frozenset(x[1:].lower() for x in parts[1:] if x.startswith("@"))
                affiliations = [x[1:].lower() for x in parts[1:] if x.startswith("&")]
                if any(not x.startswith(("@", "&")) for x in parts[1:]):
                    raise ValueError(f"Unexpected token: {path.name}:{number}")
                domain = domain.strip() if kind == "regexp" else domain.lower().strip(".")
                record = (kind, domain, tuple(sorted(attrs)), path.name, number)
                entries.append(("rule", record))
                for affiliate in affiliations:
                    self.affiliations[affiliate].add(record)
            self.files[path.name.lower()] = entries

    def resolve(self, name, stack=()):
        name = name.lower()
        if name in self.cache:
            return self.cache[name]
        if name in stack:
            raise ValueError("Cyclic GeoSite include: " + " > ".join((*stack, name)))
        if name not in self.files and name not in self.affiliations:
            raise FileNotFoundError(f"GeoSite category missing: {name}")
        records = set(self.affiliations.get(name, ()))
        for entry in self.files.get(name, ()):
            if entry[0] == "rule":
                records.add(entry[1])
            else:
                _, target, selectors = entry
                for record in self.resolve(target, (*stack, name)):
                    if matches_filters(set(record[2]), selectors):
                        records.add(record)
        self.cache[name] = frozenset(records)
        return self.cache[name]

    def select(self, specification):
        name, at, attribute = specification.partition("@")
        records = self.resolve(name)
        if at:
            selectors = (attribute.lower(),)
            records = {r for r in records if matches_filters(set(r[2]), selectors)}
        if not records:
            raise ValueError(f"GeoSite category empty: {specification}")
        return records


def is_covered(host, rules):
    return any(
        (type_id == 2 and (host == value or host.endswith("." + value)))
        or (type_id == 3 and value in host)
        for type_id, value in rules
    )


def convert(records):
    rules = {(2 if kind == "domain" else 3, value)
             for kind, value, _, _, _ in records if kind in ("domain", "keyword")}
    exact, regex = [], []
    for kind, value, _, file, line in sorted(records):
        if kind == "full":
            exact.append((value, file, line))
        elif kind == "regexp":
            regex.append((value, file, line))
    safe_regex = []
    for pattern, file, line in regex:
        suffix = equivalent_suffix(pattern)
        if suffix:
            rules.add((2, suffix))
            safe_regex.append((pattern, file, line))
    covered, unsupported = [], []
    for value, file, line in exact:
        item = {"file": file, "line": line, "type": "full", "value": value}
        if is_covered(value, rules):
            covered.append(item)
        else:
            unsupported.append({**item, "reason": "exact-only unsupported; suffix would overmatch"})
    safe_regex = set(safe_regex)
    for value, file, line in regex:
        if (value, file, line) not in safe_regex:
            unsupported.append({
                "file": file, "line": line, "type": "regexp", "value": value,
                "reason": "not provably equivalent to suffix"
            })
    for kind, value, _, file, line in sorted(records):
        if kind not in ("domain", "keyword", "full", "regexp"):
            unsupported.append({
                "file": file, "line": line, "type": kind, "value": value,
                "reason": "unsupported upstream rule type"
            })
    return rules, covered, safe_regex, unsupported


def previous_rule_count(path):
    if not path.exists():
        return None
    return sum(bool(re.match(r"^[23],\s*\S", line)) for line in
               path.read_text(encoding="utf-8").splitlines())


def conflict_report(all_rules):
    """Report exact collisions and suffix ancestry across different policies."""
    groups = defaultdict(set)
    for name, rules in all_rules.items():
        for rule in rules:
            groups[rule].add(name)
    identical = [
        {"type": key[0], "value": key[1], "sets": sorted(owners)}
        for key, owners in sorted(groups.items())
        if len(owners) > 1
    ]
    suffix_index = {domain: names for (kind, domain), names in groups.items() if kind == 2}
    shadow = []
    for domain, owners in sorted(suffix_index.items()):
        bits = domain.split(".")
        for i in range(1, len(bits)):
            ancestor = ".".join(bits[i:])
            if ancestor in suffix_index and owners != suffix_index[ancestor]:
                shadow.append({
                    "more_specific": domain, "sets": sorted(owners),
                    "less_specific": ancestor, "other_sets": sorted(suffix_index[ancestor])
                })
                break
    return {
        "note": "Diagnostic only: Anywhere uses priority tiers, then suffix specificity; "
                "this is NOT Mihomo's ordered first-match semantics.",
        "identical_count": len(identical), "identical_sample": identical[:100],
        "suffix_overlap_count": len(shadow), "suffix_overlap_sample": shadow[:100],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("rules"))
    parser.add_argument("--min-retained", type=float, default=0.7,
                        help="Reject if a generated set falls below this fraction of existing rules")
    args = parser.parse_args()
    if not 0 < args.min_retained <= 1:
        parser.error("--min-retained must be in (0, 1]")
    database = DomainLists(args.source)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"source": "v2fly/domain-list-community",
              "note": "Unsupported exact/regex entries are not widened to suffix matches.",
              "targets": {}}
    all_rules = {}
    outputs = {}
    for name, (categories, routing) in TARGETS.items():
        records = set().union(*(database.select(category) for category in categories))
        rules, covered, safe_regex, unsupported = convert(records)
        if not 0 < len(rules) <= 100000:
            raise ValueError(f"{name}: invalid rule count {len(rules)}")
        old_count = previous_rule_count(args.output / f"{name}.arrs")
        if old_count and len(rules) < old_count * args.min_retained:
            raise ValueError(f"{name}: suspicious rules drop {old_count} -> {len(rules)}")
        all_rules[name] = rules
        lines = [f"name = GeoSite {name}", f"routing = {routing}", "",
                 "# Force proxy requires explicit PROXY selection in Anywhere."]
        lines += [f"{kind}, {value}" for kind, value in sorted(rules)]
        outputs[f"{name}.arrs"] = "\n".join(lines) + "\n"
        report["targets"][name] = {
            "source_categories": categories, "rules_generated": len(rules),
            "full_already_covered": len(covered),
            "regexp_safely_converted": len(safe_regex),
            "unsupported_count": len(unsupported), "unsupported": unsupported,
        }
        print(f"{name}: {len(rules)} rules; {len(unsupported)} unsupported")
    report["conflicts"] = conflict_report(all_rules)
    try:
        report["upstream_commit"] = subprocess.check_output(
            ["git", "-C", str(args.source.parent), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        report["upstream_commit"] = None
    # Only publish generated files after every target passes validation.
    for name, body in outputs.items():
        (args.output / name).write_text(body, encoding="utf-8")
    (args.output / "conversion-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Source commit: {report['upstream_commit']}")
    print(f"Identical conflicts: {report['conflicts']['identical_count']}; "
          f"suffix overlaps: {report['conflicts']['suffix_overlap_count']}")


if __name__ == "__main__":
    main()
