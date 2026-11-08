# Anywhere GeoSite auto updater

[简体中文](README.zh-CN.md) | English

Every day at 03:25 UTC, GitHub Actions fetches [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community), converts supported domain categories into [Anywhere](https://github.com/NodePassProject/Anywhere) `.arrs` subscriptions, and commits changes.

| GeoSite source | Generated file | Routing |
| --- | --- | --- |
| google, microsoft, oracle | [force-proxy.arrs](rules/force-proxy.arrs) | **PROXY (set manually)** |
| cn | [cn.arrs](rules/cn.arrs) | DIRECT |
| private | [private.arrs](rules/private.arrs) | DIRECT |
| steam@cn | [steam-cn.arrs](rules/steam-cn.arrs) | DIRECT |
| category-ads-all | [ads.arrs](rules/ads.arrs) | REJECT |
| category-stun | [stun.arrs](rules/stun.arrs) | REJECT |

Subscription URL example (after first successful run):

`https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/force-proxy.arrs`

To run: **Actions → Update GeoSite for Anywhere → Run workflow**. For automated commit permissions, check **Settings → Actions → General → Workflow permissions → Read and write permissions**.

**Important:** This is a lossy conversion, not native GeoSite support. Domain suffix and keyword rules transfer; exact domains already matched by a broader included suffix/keyword are recorded as covered, and only provably equivalent regexes are converted. Other exact domains and regexes remain unsupported and are reported per rule set in `rules/conversion-report.json`. Include/attribute selection may differ from the actual GeoSite build. GeoIP, DNS, network/UDP, port and AND rules cannot be expressed as `.arrs`. `routing = 0` means Default, **not** PROXY: assign force-proxy to explicit PROXY in Anywhere after import. Activate Rule mode. GitHub publishing does not itself force Anywhere to refresh; that depends on the client's subscription refresh.

For local testing:

```sh
git clone --depth 1 https://github.com/v2fly/domain-list-community.git /tmp/geosite-source
python3 scripts/convert.py /tmp/geosite-source/data --output rules
```

## Single module subscription

Import **all six rule sets** from one URL:

`https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod`

Anywhere deep link:

`anywhere://add-module?link=https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod`

Or mount that .amod URL in OpenList and use the direct file URL ending in `.amod`. The module updates alongside the six .arrs files on future scheduled GitHub Actions runs. The first module file was generated from the currently published rule sets. **Set GeoSite force-proxy to PROXY in Anywhere after import**; `routing = 0` defaults to the default route.

The converter now resolves upstream `&affiliation` membership, filtered `include:` references, and attributed entries. The report records the upstream commit SHA plus cross-list collisions. GitHub Actions runs regression tests before publishing and stops on suspicious rule-count drops (below 70% of the previous version). These checks do not guarantee identical routing semantics to Mihomo, nor do they add full-domain / regex support to Anywhere.
