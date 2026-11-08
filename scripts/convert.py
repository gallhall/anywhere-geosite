#!/usr/bin/env python3
"""Convert GeoSite categories to Anywhere .arrs without unsafe widening.

Anywhere supports domain suffix (2) and keyword (3), but not exact domains
or arbitrary regular expressions. We report unsupported rules per target.
"""
import argparse
import json
import re
from pathlib import Path

TARGETS = {
    "force-proxy": (["google", "microsoft", "oracle"], 0),
    "cn": (["cn"], 1),
    "private": (["private"], 1),
    "steam-cn": (["steam@cn"], 1),
    "ads": (["category-ads-all"], 2),
    "stun": (["category-stun"], 2),
}
# Converts ONLY anchored regex with optional subdomain prefix and literal DNS
# labels, such as ^(?:.*\\.)?example\\.com$. Never approximate other regexes.
SAFE_SUFFIX_REGEX = re.compile(
    r"^\^\(\?:\.\*\\\.\)\?((?:[a-z0-9-]+\\\.)+[a-z0-9-]+)\$$",
    flags=re.I,
)
VALID_HOST = re.compile(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$", flags=re.I)


def equivalent_suffix(regex):
    match = SAFE_SUFFIX_REGEX.fullmatch(regex)
    if not match:
        return None
    candidate = match.group(1).replace(r"\.", ".").lower()
    return candidate if VALID_HOST.fullmatch(candidate) else None


def collect(name, root, stack=(), filters=()):
    name = name.lower()
    if name in stack:
        raise ValueError("Cyclic include: " + " > ".join((*stack, name)))
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(f"GeoSite category missing: {name}")
    records = set()
    for lineno, original in enumerate(path.read_text(encoding="utf8").splitlines(), 1):
        line = original.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        head = parts[0]
        attrs = {p[1:].lower() for p in parts[1:] if p.startswith("@")}
        kind, sep, value = head.partition(":")
        if not sep:
            kind, value = "domain", head
        if kind == "include":
            selectors = tuple(p[1:].lower() for p in parts[1:] if p.startswith("@"))
            records.update(collect(value, root, (*stack, name), (*filters, *selectors)))
            continue
        if any((f[1:] in attrs if f.startswith("-") else f not in attrs) for f in filters):
            continue
        value = value.lower().strip() if kind == "regexp" else value.lower().strip(".")
        if value:
            records.add((kind, value, name, lineno))
    return records


def is_covered(host, rules):
    return any(
        (type_id == 2 and (host == pattern or host.endswith("." + pattern)))
        or (type_id == 3 and pattern in host)
        for type_id, pattern in rules
    )


def convert(records):
    rules = {(2 if kind == "domain" else 3, value)
             for kind, value, _, _ in records if kind in ("domain", "keyword")}
    exact = []
    regex = []
    for kind, value, source, line in sorted(records):
        if kind == "full":
            exact.append((value, source, line))
        elif kind == "regexp":
            regex.append((value, source, line))
    # A regex may be converted only when it is provably equivalent to suffix matching.
    converted_regex = []
    for pattern, source, line in regex:
        suffix = equivalent_suffix(pattern)
        if suffix:
            rules.add((2, suffix))
            converted_regex.append((pattern, source, line))
    covered = []
    unsupported = []
    for value, source, line in exact:
        entry = {"file": source, "line": line, "type": "full", "value": value}
        if is_covered(value, rules):
            covered.append(entry)
        else:
            unsupported.append({**entry, "reason": "exact domain unsupported; suffix would overmatch"})
    converted_regex_set = set(converted_regex)
    for value, source, line in regex:
        if (value, source, line) not in converted_regex_set:
            unsupported.append({
                "file": source, "line": line, "type": "regexp", "value": value,
                "reason": "not provably equivalent to Anywhere suffix or keyword"
            })
    for kind, value, source, line in sorted(records):
        if kind not in ("domain", "keyword", "full", "regexp"):
            unsupported.append({
                "file": source, "line": line, "type": kind, "value": value,
                "reason": "unknown GeoSite rule type"
            })
    return rules, covered, converted_regex, unsupported


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("rules"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "source": "v2fly/domain-list-community",
        "note": "Covered exact entries already match a domain/keyword rule; "
                "unsupported entries are not added to avoid false positives.",
        "targets": {},
    }
    for target, (categories, action) in TARGETS.items():
        records = set()
        for entry in categories:
            name, sep, attribute = entry.partition("@")
            selected = collect(name, args.source, filters=(attribute,) if sep else ())
            if not selected:
                raise ValueError(f"GeoSite category {entry} generated zero records")
            records.update(selected)
        rules, covered, converted_regex, unsupported = convert(records)
        if not 0 < len(rules) <= 100000:
            raise ValueError(f"{target}: invalid Anywhere rule count {len(rules)}")
        lines = [f"name = GeoSite {target}", f"routing = {action}", "",
                 "# Generated automatically. Force proxy needs explicit PROXY in Anywhere."]
        lines.extend(f"{kind}, {value}" for kind, value in sorted(rules))
        (args.output / f"{target}.arrs").write_text("\n".join(lines) + "\n", encoding="utf8")
        report["targets"][target] = {
            "source_categories": categories,
            "rules_generated": len(rules),
            "full_already_covered": len(covered),
            "regexp_safely_converted": len(converted_regex),
            "unsupported_count": len(unsupported),
            "unsupported": unsupported,
        }
        print(f"{target}: {len(rules)} rules, {len(covered)} full covered, "
              f"{len(converted_regex)} regex converted, {len(unsupported)} unsupported")
    (args.output / "conversion-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("Unsupported entries across target sets:",
          sum(x["unsupported_count"] for x in report["targets"].values()))


if __name__ == "__main__":
    main()
