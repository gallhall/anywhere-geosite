#!/usr/bin/env python3
"""Build a single Anywhere .amod module from generated .arrs rules."""
import argparse
import json
from pathlib import Path

ORDER = ("force-proxy", "cn", "private", "steam-cn", "ads", "stun")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, default=Path("rules"))
    parser.add_argument("--output", type=Path, default=Path("rules/anywhere-geosite.amod"))
    args = parser.parse_args()
    sections = [
        "name = GeoSite for Anywhere",
        "description = GeoSite categories auto-updated daily; assign Force Proxy to PROXY in Anywhere.",
        "",
    ]
    estimate = []
    for item in ORDER:
        p = args.rules / f"{item}.arrs"
        source = p.read_text(encoding="utf-8")
        valid = []
        action = "0"
        for raw in source.splitlines():
            stripped = raw.strip()
            if stripped.startswith("routing ="):
                action = stripped.split("=", 1)[1].strip()
            elif stripped and not stripped.startswith("#") and stripped[0].isdigit():
                pieces = stripped.split(",", 1)
                if len(pieces) != 2 or pieces[0] not in ("0", "1", "2", "3") or not pieces[1].strip():
                    raise ValueError(f"Invalid rule in {p}: {raw}")
                valid.append(stripped)
        if not valid or len(valid) > 100000:
            raise ValueError(f"Invalid count in {p}: {len(valid)}")
        display = {
            "force-proxy": "GeoSite Force Proxy",
            "cn": "GeoSite CN",
            "private": "GeoSite Private",
            "steam-cn": "GeoSite Steam CN",
            "ads": "GeoSite Ads",
            "stun": "GeoSite STUN",
        }[item]
        sections.extend(["[Routing]", f"name = {display}", f"routing = {action}", *valid, ""])
        estimate.append({"id": item, "name": display, "rules": valid})
        print(f"{display}: {len(valid)} rules")
    # Conservative payload safeguard. Official Anywhere module sync limit is 900 KB
    # of encoded JSON, whose exact shape is internal to the client.
    estimate_bytes = len(json.dumps(estimate, ensure_ascii=False).encode("utf-8"))
    if estimate_bytes > 750000:
        raise ValueError(f"Estimated module JSON is too large: {estimate_bytes} bytes")
    module = "\n".join(sections) + "\n"
    if len(module.encode("utf-8")) > 900000:
        raise ValueError("Module exceeds 900 KB safeguard")
    parsed = module.split("[Routing]\n")[1:]
    if len(parsed) != len(ORDER):
        raise ValueError("Module section count mismatch")
    for i, section in enumerate(parsed):
        expected = len(estimate[i]["rules"])
        actual = sum(line.startswith(("2, ", "3, ")) for line in section.splitlines())
        if expected != actual:
            raise ValueError(f"Module rule mismatch: {ORDER[i]}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(module, encoding="utf-8")
    print(f"Wrote {args.output}, approx JSON budget {estimate_bytes} bytes")

if __name__ == "__main__":
    main()
