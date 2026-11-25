# -*- coding: utf-8 -*-
"""生成国内源：cn/cn.m3u + cn/cn-epg.xml.gz

国内直播源：Guovin/iptv-api（1,600+ 条，含央视频道/卫视/地方台/港台）。
节目单：合并三份中文 XMLTV —— myepg.gz(gitee)、epg.112114.xyz/pp.xml、fanmingming/live/e.xml。

mytv-android 的节目单匹配规则是「display-name == m3u 频道名」（新版优先 tvg-id），
所以这里让 XMLTV 的 <channel id> = m3u 的 tvg-id、<display-name> = 清洗后的 tvg-name，
两条匹配路径都成立。
"""
import os, sys, re, gzip, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import parse_m3u, clean_name, norm_key, esc, iter_xmltv_channels, iter_xmltv_programmes

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
WORK = os.path.join(ROOT, 'work')
OUT = os.path.join(ROOT, 'cn')
os.makedirs(OUT, exist_ok=True)

CN_M3U = os.path.join(WORK, 'guovin_cn.m3u')
EPG_FILES = [
    os.path.join(WORK, 'myepg.gz'),
    os.path.join(WORK, 'pp.xml'),
    os.path.join(WORK, 'fm_e.xml'),
]
RAW_BASE = 'https://raw.githubusercontent.com/yjw94ss/iptv-tv/main'


def load_epg_names(path):
    names = collections.defaultdict(list)
    for cid, dn, blk in iter_xmltv_channels(path):
        for x in re.findall(r'<display-name[^>]*>(.*?)</display-name>', blk, re.S):
            x = x.strip()
            if x:
                names[norm_key(x)].append(cid)
    return names


def main():
    rows = parse_m3u(CN_M3U)
    rows = [r for r in rows if not re.match(r'^\d{4}-\d{2}-\d{2}', r['name'])]

    epg_names = collections.defaultdict(list)
    for p in EPG_FILES:
        if not os.path.exists(p):
            print('跳过（不存在）:', p)
            continue
        for k, v in load_epg_names(p).items():
            epg_names[k].extend(v)
        print('已索引 EPG:', os.path.basename(p), '累计频道名', len(epg_names))

    out_rows = []
    name_idx = {}
    for r in rows:
        nm = clean_name(r['name'])
        if not nm:
            continue
        tvg = r['tvg_id'] or nm
        rec = {'name': nm, 'tvg_id': tvg, 'tvg_name': nm,
               'group': r['group'] or '其他', 'logo': r['logo'], 'urls': [r['url']]}
        if nm in name_idx:
            out_rows[name_idx[nm]]['urls'].append(r['url'])
        else:
            name_idx[nm] = len(out_rows)
            out_rows.append(rec)

    mapping = {}
    for rec in out_rows:
        cands = {norm_key(rec['tvg_name']), norm_key(rec['tvg_id']),
                 norm_key(re.sub(r'[-_]', '', rec['tvg_name']))}
        found = []
        for c in cands:
            if c and c in epg_names:
                found.extend(epg_names[c])
        if found:
            mapping[rec['tvg_id']] = sorted(set(found))
    print('国内频道 %d 条，命中节目单 %d 条' % (len(out_rows), len(mapping)))

    lines = ['#EXTM3U x-tvg-url="%s/cn/cn-epg.xml.gz"' % RAW_BASE]
    for rec in out_rows:
        attrs = 'tvg-id="%s" tvg-name="%s"' % (rec['tvg_id'], rec['tvg_name'])
        if rec['logo']:
            attrs += ' tvg-logo="%s"' % rec['logo']
        attrs += ' group-title="%s"' % rec['group']
        for u in rec['urls']:
            lines.append('#EXTINF:-1 %s,%s' % (attrs, rec['name']))
            lines.append(u)
    with open(os.path.join(OUT, 'cn.m3u'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    # 反查 EPG id -> m3u id
    inv = {}
    for m3u_id, epg_ids in mapping.items():
        for e in epg_ids:
            inv.setdefault(e, m3u_id)
    prog = collections.defaultdict(list)
    for p in EPG_FILES:
        if not os.path.exists(p):
            continue
        n = 0
        for ch, st, sp, title, desc in iter_xmltv_programmes(p):
            if ch in inv:
                prog[inv[ch]].append((st, sp, title))
                n += 1
        print('已读节目条目:', os.path.basename(p), n)

    id2name = {rec['tvg_id']: rec['tvg_name'] for rec in out_rows}
    with gzip.open(os.path.join(OUT, 'cn-epg.xml.gz'), 'wb', compresslevel=6) as gz:
        gz.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        gz.write(b'<tv generator-info-name="yjw94ss/iptv-tv">\n')
        for m3u_id in mapping:
            gz.write(('<channel id="%s"><display-name>%s</display-name></channel>\n'
                      % (esc(m3u_id), esc(id2name.get(m3u_id, m3u_id)))).encode())
        for m3u_id in mapping:
            seen = set()
            for st, sp, title in prog.get(m3u_id, []):
                if st in seen:
                    continue
                seen.add(st)
                gz.write(('<programme start="%s" stop="%s" channel="%s"><title>%s</title></programme>\n'
                          % (st, sp, esc(m3u_id), esc(title))).encode())
        gz.write(b'</tv>\n')
    print('写出 cn/cn.m3u (%d 行) 与 cn/cn-epg.xml.gz (%d KB)'
          % (len(out_rows), os.path.getsize(os.path.join(OUT, 'cn-epg.xml.gz')) // 1024))


if __name__ == '__main__':
    main()
