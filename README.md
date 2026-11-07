# Anywhere GeoSite auto updater

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

**Important:** This is a lossy conversion, not native GeoSite support. Domain suffix and keyword rules transfer; exact domains and regular expressions are skipped and listed in `rules/conversion-report.json`. Include/attribute selection may differ from the actual GeoSite build. GeoIP, DNS, network/UDP, port and AND rules cannot be expressed as `.arrs`. `routing = 0` means Default, **not** PROXY: assign force-proxy to explicit PROXY in Anywhere after import. Activate Rule mode. GitHub publishing does not itself force Anywhere to refresh; that depends on the client's subscription refresh.

For local testing:

```sh
git clone --depth 1 https://github.com/v2fly/domain-list-community.git /tmp/geosite-source
python3 scripts/convert.py /tmp/geosite-source/data --output rules
```
