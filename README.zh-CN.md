# Anywhere GeoSite 规则自动更新（中文说明）

[English](README.md) | **简体中文**

本仓库使用 **GitHub Actions** 每天检查 [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) 上游域名规则，并将部分 GeoSite 分类转换成适用于 [Anywhere](https://github.com/NodePassProject/Anywhere) 的 `.arrs` 文件，同时生成一个合并模块 `.amod`。

**无需每天重新导入。** 只要订阅地址不变，GitHub 文件更新后，Anywhere 在刷新订阅时即可获取新内容（受到客户端与中间缓存影响）。

> [!IMPORTANT]
> 这是 **GeoSite 数据转换**，**不是**让 Anywhere 原生支持 `geosite.dat`、Mihomo 的 `GEOSITE` 语法或整份 Mihomo YAML 配置。转换并非完全无损，请阅读下方限制。

## 一、推荐：一次导入全部规则

六组规则已打包为一个文件：

**[anywhere-geosite.amod](https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod)**

订阅 URL：

```text
https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod
```

可尝试使用 Anywhere 的深层链接打开：

```text
anywhere://add-module?link=https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod
```

如果系统没有唤起 Anywhere，可在 Anywhere 的模块管理页面使用 URL 手动导入。导入前检查预览，确认包含六组规则。**开启 Anywhere 的 Rule（规则）路由模式**，并检查各规则集策略。

### 规则对应关系

| 生成文件 | 上游 GeoSite 分类 | 应使用的路由策略 |
| --- | --- | --- |
| `force-proxy.arrs` | `google` + `microsoft` + `oracle` | **PROXY：导入后必须手动指定代理出口** |
| `cn.arrs` | `cn` | DIRECT（直连） |
| `private.arrs` | `private` | DIRECT（直连） |
| `steam-cn.arrs` | `steam@cn` | DIRECT（直连） |
| `ads.arrs` | `category-ads-all` | REJECT（拒绝） |
| `stun.arrs` | `category-stun` | REJECT（拒绝） |

`force-proxy.arrs` 当前使用 `routing = 0`，表示 **Default（默认路由）而非强制代理**。必须在 Anywhere 中手动将 `GeoSite force-proxy` 改为 **PROXY**。并检查强制代理优先于中国直连，拒绝规则优先于一般放行规则。

如果只需要部分分类，可分别订阅 `rules/` 下对应的 `.arrs` 文件，而不导入合并模块。

## 二、通过 OpenList 的 UrlTree（地址树）订阅

不必把 `.amod` 文件手动下载并上传到网盘，也不用每次上游更新后重新上传。

1. 进入 OpenList 管理后台 → **存储** → **添加**。
2. 驱动选择 **UrlTree（地址树）**，挂载路径例如 `/GeoSite`。
3. 在 URL Structure（URL 结构）里填写合并模块的原始文件 URL：

   ```text
   https://raw.githubusercontent.com/gallhall/anywhere-geosite/main/rules/anywhere-geosite.amod
   ```

4. 保存后，在浏览器中验证 OpenList 是否能下载该文件。如果文件位于 `/GeoSite/anywhere-geosite.amod`，直链**可能**类似：

   ```text
   https://你的OpenList域名/d/GeoSite/anywhere-geosite.amod
   ```

   最终路径取决于 OpenList 的实际挂载、反向代理及访问权限。请使用**直接返回 UTF-8 文件内容**的链接，而不是文件预览页或登录页。

5. 把经验证的 OpenList 直链作为 Anywhere 的模块订阅 URL 导入。

**缓存注意：** GitHub 文件更新后，UrlTree 仍引用同一 URL，通常不用改配置；但 OpenList、CDN、反向代理以及 Anywhere 均可能缓存旧内容。必要时刷新 Anywhere 订阅并检查缓存规则。OpenList 的目录缓存时间不等于远程文件内容的强制刷新间隔。

## 三、自动更新流程

```text
GeoSite 上游数据库
        ↓
GitHub Actions 每天检查
        ↓
scripts/convert.py 转换成 6 个 .arrs
        ↓
scripts/bundle_module.py 打包为 anywhere-geosite.amod
        ↓
提交更新到 main / rules/
        ↓
Anywhere 刷新模块订阅
```

- **检查时间**：每天 **UTC 03:25**，即北京时间 **11:25**；GitHub Actions 定时任务可能延迟。
- **没有变化**：工作流不会创建无意义的提交。
- **手动运行**：进入 [Actions → Update GeoSite for Anywhere](https://github.com/gallhall/anywhere-geosite/actions/workflows/update.yml)，点击 **Run workflow**。
- **提交权限**：如果工作流提示无法推送，请在 GitHub 仓库 **Settings → Actions → General → Workflow permissions** 检查是否允许 `Read and write permissions`。
- **客户端刷新**：GitHub Actions 只负责更新 GitHub 文件，**不能直接命令 Anywhere 立即刷新**。是否支持定时刷新由你的 Anywhere 版本及设置决定。

## 四、与原始 Mihomo 配置的区别

原来 Mihomo 使用的规则包含：

```yaml
- GEOSITE,category-ads-all,REJECT
- GEOSITE,private,DIRECT
- GEOSITE,category-stun,REJECT
- GEOSITE,steam@cn,DIRECT
- RULE-SET,force-proxy,PROXY
- GEOSITE,CN,DIRECT
- GEOIP,CN,DIRECT
- AND,((NETWORK,UDP),(DST-PORT,443)),REJECT
- MATCH,PROXY
```

本项目只转换了其中能够近似表示为 **域名规则** 的部分，**没有转换**：

- `GEOIP,CN` / 私有 IP 的 IP 地理位置判断。
- `NETWORK,UDP`、`DST-PORT`、`AND` 等端口与协议组合条件。
- Mihomo 的 DNS、Fake-IP、按域名选择 DNS 服务器等设置。
- `MATCH,PROXY` 的默认出口设定（需在 Anywhere 内单独配置）。
- GeoSite 的全部原生匹配语义：`full`（精确域名）、`regexp`（正则表达式）等无法等价表达的条目会跳过，某些 include / 属性匹配也可能与 Mihomo 使用的编译结果不同。

转换统计记录在 [rules/conversion-report.json](rules/conversion-report.json)。**不要把本项目当作网络泄漏防护或完整的 QUIC/STUN 屏蔽保证**；涉及 UDP、DNS、防泄漏等功能，需要在 Anywhere 中另行配置和测试。

## 五、本地运行（可选）

在有 Git、Python 3 的设备上：

```bash
git clone --depth 1 https://github.com/v2fly/domain-list-community.git /tmp/geosite-source
python3 scripts/convert.py /tmp/geosite-source/data --output rules
python3 scripts/bundle_module.py --rules rules --output rules/anywhere-geosite.amod
```

## 六、文件目录

```text
.github/workflows/update.yml      # 定时自动更新
scripts/convert.py                # GeoSite 转 .arrs
scripts/bundle_module.py          # 六组规则合并为 .amod
rules/anywhere-geosite.amod       # 推荐：单文件订阅
rules/force-proxy.arrs
rules/cn.arrs
rules/private.arrs
rules/steam-cn.arrs
rules/ads.arrs
rules/stun.arrs
rules/conversion-report.json      # 转换统计
README.md                         # 英文说明
README.zh-CN.md                   # 中文说明
```

## 相关项目

- [Anywhere](https://github.com/NodePassProject/Anywhere)
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)

本项目是社区转换方案，不代表与上述项目官方存在关联。
