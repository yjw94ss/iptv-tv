# -*- coding: utf-8 -*-
"""共享工具：名称清洗、m3u 解析、XMLTV 读写。"""
import re, gzip, os

QUALITY_TOKENS = [
    '超高清', '超清', '高清', '标清', '蓝光', '真高清', '极清',
    'FULLHD', 'FHD', 'UHD', 'HD', 'SD', '4K', '8K', '2160P', '1440P',
    '1080P', '1080I', '720P', '576P', '480P', '360P', 'HEVC', 'H265',
]
PAREN_QUALITY = re.compile(r'[\(\[（【]\s*[^()\[\]（）【】]{0,18}?(?:' + '|'.join(QUALITY_TOKENS) + r')\s*[\)\]）】]', re.I)
BRACKET_WORDS = re.compile(r'[\(\[（【]\s*(?:HD|SD|4K|UHD|FHD|1080P?|720P?|直播|备用|线路|高清|标清|超清)\s*[\)\]）】]', re.I)
TRAIL_QUALITY = re.compile(r'[\s\-_·|]+(?:' + '|'.join(QUALITY_TOKENS) + r')$', re.I)
LEAD_QUALITY = re.compile(r'^(?:' + '|'.join(QUALITY_TOKENS) + r')[\s\-_·|]+', re.I)
PAREN_ANY = re.compile(r'[\(\[（【][^()\[\]（）【】]{0,24}[\)\]）】]')


def clean_name(name):
    """清洗频道名：去掉分辨率/画质后缀、括注多余说明，压缩空白。"""
    if not name:
        return ''
    s = name.strip()
    s = s.replace(' ', ' ')
    # 去掉整体括注（如 "(720p)"、"(1080P HD)"、"（高清）"）
    prev = None
    while prev != s:
        prev = s
        s = PAREN_QUALITY.sub('', s)
        s = BRACKET_WORDS.sub('', s)
    # 去掉尾部画质词
    s = TRAIL_QUALITY.sub('', s)
    s = LEAD_QUALITY.sub('', s)
    # 去掉剩余的空括注
    s = re.sub(r'[\(\[]\s*[\)\]]', '', s)
    s = re.sub(r'\s{2,}', ' ', s).strip(' -_|·,，')
    return s


def norm_key(name):
    """用于 EPG 名称匹配的归一化键：去空格与标点、去画质词、大写。"""
    s = (name or '').upper()
    s = re.sub(r'[\s\-_·、,，.。;；:：!！?？\'"“”‘’()（）\[\]【】/\\|]+', '', s)
    for t in QUALITY_TOKENS:
        s = s.replace(t.upper(), '')
    return s


def parse_m3u(path):
    """返回 [{'name','tvg_id','tvg_name','group','logo','url','attrs'}]"""
    rows = []
    cur = None
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n').rstrip('\r')
            if not line.strip():
                continue
            if line.startswith('#EXTINF'):
                body = line[8:]
                attrs = {}
                for m in re.finditer(r'([\w-]+)="([^"]*)"', body):
                    attrs[m.group(1)] = m.group(2)
                name = body.split(',')[-1].strip()
                cur = {
                    'name': name,
                    'tvg_id': attrs.get('tvg-id', ''),
                    'tvg_name': attrs.get('tvg-name', ''),
                    'group': attrs.get('group-title', ''),
                    'logo': attrs.get('tvg-logo', ''),
                    'attrs': attrs,
                    'url': None,
                }
            elif line.startswith('#'):
                continue
            else:
                if cur is not None and cur['url'] is None:
                    cur['url'] = line.strip()
                    rows.append(cur)
                    cur = None
    return rows


def attr_escape(v):
    return (v or '').replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def write_m3u(path, rows, header_extra=''):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U' + header_extra + '\n')
        for r in rows:
            a = []
            if r.get('tvg_id'):
                a.append('tvg-id="%s"' % attr_escape(r['tvg_id']))
            if r.get('tvg_name'):
                a.append('tvg-name="%s"' % attr_escape(r['tvg_name']))
            if r.get('logo'):
                a.append('tvg-logo="%s"' % attr_escape(r['logo']))
            if r.get('group'):
                a.append('group-title="%s"' % attr_escape(r['group']))
            f.write('#EXTINF:-1 %s,%s\n' % (' '.join(a), r['name']))
            f.write(r['url'] + '\n')


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def iter_xmltv_channels(path):
    """流式产出 (id, display_name) —— path 可以是 .xml 或 .xml.gz"""
    op = gzip.open if str(path).endswith('.gz') else open
    buf = ''
    with op(path, 'rb') as f:
        chunk = f.read(1 << 20)
        while chunk:
            buf += chunk.decode('utf-8', 'replace')
            # 逐个 channel 块处理
            while True:
                i = buf.find('<channel ')
                if i < 0:
                    break
                j = buf.find('</channel>', i)
                if j < 0:
                    break
                blk = buf[i:j]
                buf = buf[j:]
                m = re.search(r'<channel\s+id="([^"]*)"', blk)
                if not m:
                    continue
                names = re.findall(r'<display-name[^>]*>(.*?)</display-name>', blk, re.S)
                yield m.group(1), (names[0] if names else ''), blk
            # 保留尾部
            keep = buf.rfind('<')
            if keep > 0:
                buf = buf[keep:]
            chunk = f.read(1 << 20)
    if buf:
        i = buf.find('<channel ')
        while i >= 0:
            j = buf.find('</channel>', i)
            if j < 0:
                break
            blk = buf[i:j]
            m = re.search(r'<channel\s+id="([^"]*)"', blk)
            if m:
                names = re.findall(r'<display-name[^>]*>(.*?)</display-name>', blk, re.S)
                yield m.group(1), (names[0] if names else ''), blk
            i = buf.find('<channel ', j)


def iter_xmltv_programmes(path):
    """流式产出 (channel_id, start, stop, title, desc)"""
    op = gzip.open if str(path).endswith('.gz') else open
    buf = ''
    with op(path, 'rb') as f:
        chunk = f.read(1 << 20)
        while chunk:
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
                d = re.search(r'<desc[^>]*>(.*?)</desc>', blk, re.S)
                yield (at.get('channel', ''), at.get('start', ''), at.get('stop', ''),
                       t.group(1) if t else '', d.group(1) if d else '')
            keep = buf.rfind('<')
            if keep > 0:
                buf = buf[keep:]
            chunk = f.read(1 << 20)
