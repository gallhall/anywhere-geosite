# Anywhere GeoSite 自动更新

**简体中文** | [English](README.md)

GitHub Actions 每天 UTC 03:25 从 [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) 获取数据，将支持的域名分类转换为 [Anywhere](https://github.com/NodePassProject/Anywhere) 的 `.arrs` 订阅规则，并提交更新。

| GeoSite 分类 | 生成文件 | 路由策略 |
| --- | --- | --- |
| google、microsoft、oracle | [force-proxy.arrs](rules/force-proxy.arrs) | **PROXY（需手动设置）** |
| cn | [cn.arrs](rules/cn.arrs) | DIRECT |
| private | [private.arrs](rules/private.arrs) | DIRECT |
| steam@cn | [steam-cn.arrs](rules/steam-cn.arrs) | DIRECT |
| category-ads-all | [ads.arrs](rules/ads.arrs) | REJECT |
| category-stun | [stun.arrs](rules/stun.arrs) | REJECT |

订阅地址示例（首次运行成功后）：

`https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/force-proxy.arrs`

手动运行：**Actions → Update GeoSite for Anywhere → Run workflow**。如需允许工作流自动提交更新，请检查 **Settings → Actions → General → Workflow permissions → Read and write permissions**。

**注意：** 此转换并非无损转换，也不代表 Anywhere 原生支持 GeoSite。域名后缀和关键词规则可以转换；已被现有后缀或关键词规则覆盖的精确域名会标记为已覆盖；只有能证明等价的正则表达式才会转换。其他精确域名与正则表达式仍不支持，并按规则集记录在 `rules/conversion-report.json` 中。include 和属性筛选结果可能与实际编译的 GeoSite 数据库不同。GeoIP、DNS、网络/UDP、端口及 AND 规则无法通过 `.arrs` 表达。`routing = 0` 代表 Default（默认），**不是** PROXY：导入后需要在 Anywhere 中将 force-proxy 明确设置为 PROXY，并启用 Rule（规则）模式。GitHub 发布更新后不会主动让 Anywhere 刷新，具体取决于客户端的订阅刷新机制。

本地测试：

```sh
git clone --depth 1 https://github.com/v2fly/domain-list-community.git /tmp/geosite-source
python3 scripts/convert.py /tmp/geosite-source/data --output rules
```

## 单模块订阅

通过一个 URL **导入全部六组规则**：

`https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod`

Anywhere 深层链接：

`anywhere://add-module?link=https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod`

也可以在 OpenList 中挂载该 `.amod` URL，并使用以 `.amod` 结尾的文件直链。此模块会在未来 GitHub Actions 定时运行时，与六个 `.arrs` 文件一同更新。首个模块文件由当时已发布的规则集生成。**导入后请在 Anywhere 中将 GeoSite force-proxy 设置为 PROXY**；`routing = 0` 表示使用默认路由。
