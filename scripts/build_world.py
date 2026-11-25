# -*- coding: utf-8 -*-
"""生成国外源：world/world.m3u + world/world-epg.xml.gz

频道清单：iptv-org index.country.m3u（13,121 行，group-title = 国家名，tvg-id 形如 `Name.cc@SD`）。
节目单：fehmi/world-epg 的 guide.xml.gz（由 iptv-org/epg 官方抓取器生成，
         channel id 与 iptv-org 的 tvg-id 完全同构，programme 时间带 +0000 时区）。

关键：XMLTV 的 <channel id> = m3u 的 tvg-id，<display-name> = 清洗后的频道名，
mytv-android 按 display-name 或 tvg-id 匹配都能命中。
"""
import os, sys, re, gzip, collections, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import parse_m3u, clean_name, esc

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
WORK = os.path.join(ROOT, 'work')
OUT = os.path.join(ROOT, 'world')
os.makedirs(OUT, exist_ok=True)

SRC_M3U = os.path.join(WORK, 'index.country.m3u')
WORLD_GUIDE = os.path.join(WORK, 'world_guide.xml.gz')
RAW_BASE = 'https://raw.githubusercontent.com/yjw94ss/iptv-tv/main'

WINDOW_BACK_H = 2
WINDOW_FWD_H = 40


def parse_xmltv_time(t):
    m = re.match(r'^(\d{14})(?:\s*([+-]\d{4}))?$', t.strip())
    if not m:
        return None
    dt = datetime.datetime.strptime(m.group(1), '%Y%m%d%H%M%S')
    off = m.group(2) or '+0000'
    sign = 1 if off[0] == '+' else -1
    delta = datetime.timedelta(hours=int(off[1:3]), minutes=int(off[3:5])) * sign
    return dt.replace(tzinfo=datetime.timezone(delta))


def iter_guide(path):
    """流式解析 guide.xml(.gz)：产出 (channel_id, start, stop, title)"""
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rb') as f:
        buf = ''
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            buf += chunk.decode('utf-8', 'replace')
            while True:
                i = buf.find('<programme ')
                if i < 0:
                    break
                j = buf.find('</programme>', i)
                if j < 0:
                    break
                blk = buf[i:j]
                buf = buf[j:]
                m = re.search(r'<programme\s+([^>]*)>', blk)
                if not m:
                    continue
                at = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
                t = re.search(r'<title[^>]*>(.*?)</title>', blk, re.S)
                if not t:
                    continue
                yield at.get('channel', ''), at.get('start', ''), at.get('stop', ''), t.group(1).strip()
            keep = buf.rfind('<')
            if keep > 0:
                buf = buf[keep:]


def main():
    rows = parse_m3u(SRC_M3U)
    out_rows = []
    for r in rows:
        nm = clean_name(r['name'])
        if not nm:
            continue
        out_rows.append({'name': nm, 'tvg_id': r['tvg_id'], 'tvg_name': nm,
                         'group': r['group'] or 'International', 'logo': r['logo'],
                         'url': r['url']})
    print('国外频道行数 %d（唯一 tvg-id %d）'
          % (len(out_rows), len({r['tvg_id'] for r in out_rows})))

    lines = ['#EXTM3U x-tvg-url="%s/world/world-epg.xml.gz"' % RAW_BASE]
    for r in out_rows:
        attrs = 'tvg-id="%s" tvg-name="%s"' % (r['tvg_id'], r['tvg_name'])
        if r['logo']:
            attrs += ' tvg-logo="%s"' % r['logo']
        attrs += ' group-title="%s"' % r['group']
        lines.append('#EXTINF:-1 %s,%s' % (attrs, r['name']))
        lines.append(r['url'])
    with open(os.path.join(OUT, 'world.m3u'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    id2name = {}
    for r in out_rows:
        id2name.setdefault(r['tvg_id'], r['tvg_name'])

    now = datetime.datetime.now(datetime.timezone.utc)
    lo = now - datetime.timedelta(hours=WINDOW_BACK_H)
    hi = now + datetime.timedelta(hours=WINDOW_FWD_H)

    prog = collections.defaultdict(list)
    for ch, st, sp, title in iter_guide(WORLD_GUIDE):
        if ch not in id2name:
            continue
        s = parse_xmltv_time(st)
        if s is None or s < lo or s > hi:
            continue
        if not title:
            continue
        prog[ch].append((st, sp, title))
    print('窗口内有效频道 %d，节目条目 %d' % (len(prog), sum(len(v) for v in prog.values())))

    with gzip.open(os.path.join(OUT, 'world-epg.xml.gz'), 'wb', compresslevel=6) as gz:
        gz.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        gz.write(b'<tv generator-info-name="yjw94ss/iptv-tv (source: iptv-org/epg)">\n')
        for ch in sorted(prog):
            gz.write(('<channel id="%s"><display-name>%s</display-name></channel>\n'
                      % (esc(ch), esc(id2name[ch]))).encode())
        for ch in sorted(prog):
            seen = set()
            for st, sp, title in prog[ch]:
                if st in seen:
                    continue
                seen.add(st)
                gz.write(('<programme start="%s" stop="%s" channel="%s"><title>%s</title></programme>\n'
                          % (st, sp, esc(ch), esc(title))).encode())
        gz.write(b'</tv>\n')
    print('写出 world/world.m3u 与 world/world-epg.xml.gz (%d KB)'
          % (os.path.getsize(os.path.join(OUT, 'world-epg.xml.gz')) // 1024))


if __name__ == '__main__':
    main()
