# 全球电视直播源（国内 / 国外分开入口）

为创维酷开电视上的 **mytv-android** 播放器准备的两套直播源与配套节目单（XMLTV），
每天自动更新一次。

## 直接可用的地址

| 用途 | 地址 |
|---|---|
| 国内直播清单 | `https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/cn/cn.m3u` |
| 国内节目单 | `https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/cn/cn-epg.xml.gz` |
| 国外直播清单 | `https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/world/world.m3u` |
| 国外节目单 | `https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/world/world-epg.xml.gz` |

## 特点

- **国内外分离**：两条独立订阅源，各自带节目单，电视上分别作为「国内」「国外」入口。
- **节目单严丝合缝**：XMLTV 的 `<channel id>` 直接取 m3u 的 `tvg-id`，
  `<display-name>` 取清洗后的频道名 —— mytv-android 按 `display-name` 或 `tvg-id`
  匹配，两条路径都能命中。
- **频道名已清洗**：去掉 `(720p)`、`HD` 等画质后缀，避免节目单对不上。
- **国内**：588 个频道，央视频道 / 各卫视 / 地方台 / 港台 / 体育，242 个频道带节目单。
- **国外**：13,121 行（11,497 个频道，230+ 国家/地区，按国家分组），3,555 个频道带节目单。

## 数据来源

| 用途 | 来源 |
|---|---|
| 国内频道 | [Guovin/iptv-api](https://github.com/Guovin/iptv-api)（自动采集 + 测速） |
| 国内节目单 | [mytv-android/myepg](https://gitee.com/mytv-android/myepg)、[epg.112114.xyz](https://epg.112114.xyz/pp.xml)、[fanmingming/live](https://github.com/fanmingming/live) |
| 国外频道 | [iptv-org/iptv](https://github.com/iptv-org/iptv) 的 `index.country.m3u` |
| 国外节目单 | [iptv-org/epg](https://github.com/iptv-org/epg) 抓取结果，经 [fehmi/world-epg](https://github.com/fehmi/world-epg) 每日重建 |

## 在 mytv-android 上使用

「首页 → 推送」打开远程面板（默认端口 10591），或直接用浏览器访问 `http://<电视IP>:10591`，
在「订阅源」里添加两条：

```
国内直播   https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/cn/cn.m3u
  EPG 地址  https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/cn/cn-epg.xml.gz
国外直播   https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/world/world.m3u
  EPG 地址  https://raw.githubusercontent.com/yjw94ss/iptv-tv/main/world/world-epg.xml.gz
```

再在「设置 → 节目单」里打开 **「优先用订阅源自带的节目单」**，即可做到
每个入口各用各的节目单。

## 更新

`.github/workflows/update.yml` 每天 03:17 UTC 重新拉取源数据、重建清单与节目单并提交。
生成脚本在 `scripts/`：

- `scripts/build_cn.py` — 国内清单 + 合并三份中文节目单
- `scripts/build_world.py` — 国外清单（按国家分组）+ 从 world-epg 抽取时间窗内节目单

## 说明

- 全部为免费公开的开路频道源，稳定性取决于各直播源自身与所在网络的可达性。
- 部分境外台有地域封锁，若在电视上打不开，多半是线路本身被限制，换线路或走旁路由代理。
- iptv-org 已于 2024-01-30 起停止分发 NSFW 频道。
