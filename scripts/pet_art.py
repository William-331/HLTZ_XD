"""Original pixel room shared by the README and the interactive home. No dependencies."""
from html import escape

CAT = (
    '..ooo...........ooo......',
    '..oFFo.........oFFo......',
    '..oFPFoo.....ooFPFo......',
    '..oFPPFo.....oFPPFo......',
    '..oFFFFoooooooFFFFo......',
    '..oFFFFFFFFFFFFFFFo......',
    '.oFFFFFFFFFFFFFFFFFo.....',
    '.oFFFFFFFFFFFFFFFFFo.....',
    '.oFFFFFFFFFFFFFFFFFo.....',
    '.oFFFFFFFFFFFFFFFFFo.....',
    '.oFFFFFFFFFFFFFFFFFo.....',
    '..oFFFFFFFFFFFFFFFo......',
    '...ooFFFFFFFFFFFoo.......',
    '....oFFFFFFFFFFFo........',
    '...oFFFFBBBBBFFFFo.......',
    '...oFFFBBBBBBBFFFo.......',
    '...oFFFBBBBBBBFFFo..ooo..',
    '...oFFFBBBBBBBFFFo.oFFo..',
    '...oFFFBBBBBBBFFFooFFo...',
    '...oFFFFBBBBBFFFFoFFo....',
    '...oFFFFFBBBFFFFFoo.....',
    '....ooooo...ooooo.......',
)

PALETTES = {
    'light': dict(wall='#eee7f2',stripe='#e7dfea',floor='#e9cbb6',line='#d6b49d',frame='#a69aaf',window='#bdcfda',glass='#d5e5e9',cloud='#fff9ed',leaf='#8da889',stem='#677f67',pot='#d5a28d',rug='#b7a3c2',rugLight='#c7b6ce',desk='#b39175',deskLight='#d6b398',monitor='#62596b',screen='#bdcfb0',ink='#514354',cream='#f2d0a0',fur='#d7a171',belly='#ffe8c6',pink='#df9b99',outline='#926e64',paper='#fcfaf5',muted='#7a7280',accent='#736184',edge='#e7e0e8'),
    'dark': dict(wall='#39323e',stripe='#3f3745',floor='#51424a',line='#6c5860',frame='#b4a3bf',window='#566782',glass='#7583a0',cloud='#c4bdd1',leaf='#839c80',stem='#b3b996',pot='#ba8c7c',rug='#78667d',rugLight='#907c94',desk='#947e70',deskLight='#b6a08b',monitor='#272830',screen='#749b85',ink='#eee8f2',cream='#ead1a7',fur='#cc9f75',belly='#f6e1bd',pink='#d89899',outline='#735a5b',paper='#22232a',muted='#b5acbd',accent='#c6b3df',edge='#49404e'),
}


def svg_open(width, height, title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>'


def room_svg(theme='light', action='idle', level=1, name='扣子'):
    p = PALETTES[theme]
    elements = [svg_open(720, 292, f'{name}的猫窝：' + {'idle':'陪你写代码','feed':'正在吃小鱼','play':'正在玩毛线球','sleep':'正在休息'}[action]), '<style>@keyframes blink{0%,90%,94%,100%{opacity:1}92%{opacity:0}}.eyes{animation:blink 5s step-end infinite}@media(prefers-reduced-motion:reduce){.eyes{animation:none}}</style>', '<g transform="scale(2)" shape-rendering="crispEdges">']

    def r(x,y,w,h,color):
        elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{p.get(color,color)}"/>')

    r(0,0,360,146,'wall')
    for x in range(0,360,15): r(x,0,1,112,'stripe')
    r(0,111,360,35,'floor'); r(0,109,360,3,'line')
    for y in range(121,146,12):
        r(0,y,360,1,'line')
        for x in range(25 if y==121 else 65,360,85): r(x,y-10,1,10,'line')
    r(35,25,73,60,'frame'); r(38,28,67,54,'window'); r(41,31,61,48,'glass')
    r(50,43,15,4,'cloud'); r(54,39,7,4,'cloud'); r(82,57,13,4,'cloud'); r(86,53,5,4,'cloud')
    r(70,28,3,54,'frame'); r(38,54,67,3,'frame'); r(30,83,83,4,'deskLight')
    r(293,31,38,3,'desk'); r(299,17,4,14,'leaf'); r(305,21,6,10,'pink'); r(313,14,4,17,'frame'); r(319,19,5,12,'deskLight')
    r(264,102,67,5,'deskLight'); r(269,107,4,23,'desk'); r(322,107,4,23,'desk')
    r(277,72,43,26,'monitor'); r(280,75,37,19,'screen'); r(295,98,7,4,'monitor'); r(288,101,22,1,'monitor')
    for y in (79,83,87): r(284,y,19 if y==83 else 11,1,'stem')
    r(285,105,27,2,'monitor')
    if level>=2:
        r(236,89,2,20,'stem'); r(229,82,7,4,'leaf'); r(226,79,7,4,'leaf'); r(238,87,7,5,'leaf'); r(241,83,6,5,'leaf'); r(235,75,4,10,'leaf'); r(229,102,17,3,'pot'); r(231,105,13,11,'pot')
    if level>=4:
        r(44,80,43,3,'rug'); r(48,77,35,3,'rugLight')
    if level>=6:
        r(130,35,21,20,'desk'); r(132,37,17,16,'cloud'); r(140,41,2,8,'fur'); r(137,44,8,2,'fur')
    if level>=2:
        r(133,125,91,10,'rug'); r(127,128,103,5,'rug'); r(139,125,79,2,'rugLight'); r(139,133,79,2,'rugLight')
    else:
        r(147,126,67,7,'pot'); r(144,123,73,4,'deskLight')
    r(112,120,15,5,'monitor'); r(110,118,19,3,'frame'); r(115,117,9,2,'screen')
    ox,oy,scale=151,(54 if action=='play' else 59),3
    for y,row in enumerate(CAT):
        for x,c in enumerate(row):
            if c!='.': r(ox+x*scale,oy+y*scale,scale,scale,dict(o='outline',F='cream',P='pink',B='belly')[c])
    r(ox+27,oy+15,3,6,'fur'); r(ox+36,oy+15,3,6,'fur')
    if action=='sleep':
        r(ox+18,oy+27,7,2,'monitor'); r(ox+42,oy+27,7,2,'monitor')
    else:
        elements.append('<g class="eyes">')
        r(ox+21,oy+24,3,6,'monitor'); r(ox+42,oy+24,3,6,'monitor'); r(ox+21,oy+24,1,2,'cloud'); r(ox+42,oy+24,1,2,'cloud')
        elements.append('</g>')
    r(ox+30,oy+30,6,3,'pink'); r(ox+33,oy+33,2,3,'monitor'); r(ox+27,oy+36,5,1,'monitor'); r(ox+36,oy+36,5,1,'monitor')
    r(ox+12,oy+30,5,2,'pink'); r(ox+48,oy+30,5,2,'pink')
    if action=='feed':
        r(132,104,13,5,'window'); r(130,102,3,3,'window'); r(130,108,3,3,'window'); r(143,104,2,2,'monitor')
    if level>=2 or action=='play':
        r(219,117,12,12,'pink'); r(222,114,6,18,'pink'); r(219,120,12,2,'cloud'); r(224,116,2,12,'cloud'); r(237,127,11,1,'pink'); r(232,125,6,1,'pink')
    if action=='sleep':
        elements.append(f'<text x="224" y="65" fill="{p["muted"]}" font-family="monospace" font-size="9">z</text><text x="235" y="52" fill="{p["muted"]}" font-family="monospace" font-size="11">Z</text>')
    r(11,30,1,5,'pot'); r(9,32,5,1,'pot'); r(341,85,1,5,'frame'); r(339,87,5,1,'frame')
    elements.append('</g></svg>')
    return ''.join(elements)


def footprint_svg(days, theme='light'):
    p=PALETTES[theme]
    out=[svg_open(490,104,'扣子最近七天的猫爪足迹；日期与贡献数以 GitHub 贡献日历为准'),f'<rect width="490" height="104" rx="8" fill="{p["paper"]}"/>']
    for i,day in enumerate(days):
        x=i*70+35; n=day['count']
        out.append(f'<g><title>{escape(day["date"])}：{n} 次贡献</title>')
        if n:
            opacity=0.5 if n<=3 else 0.75 if n<=9 else 1
            out.append(f'<g fill="{p["accent"]}" opacity="{opacity}"><ellipse cx="{x}" cy="40" rx="9" ry="7"/><ellipse cx="{x-10}" cy="29" rx="3" ry="4"/><ellipse cx="{x-3}" cy="25" rx="3" ry="4"/><ellipse cx="{x+5}" cy="25" rx="3" ry="4"/><ellipse cx="{x+12}" cy="30" rx="3" ry="4"/></g>')
        else:
            out.append(f'<path d="M{x+7},22 A13,13 0 1,0 {x+9},45 A15,15 0 0,1 {x+7},22" fill="{p["frame"]}"/>')
        out.append(f'<text x="{x}" y="72" text-anchor="middle" fill="{p["ink"]}" font-size="17" font-family="Segoe UI,Microsoft YaHei,sans-serif">{escape(day["date"][5:])}</text><text x="{x}" y="95" text-anchor="middle" fill="{p["muted"]}" font-size="16" font-family="Segoe UI,Microsoft YaHei,sans-serif">{n} 次</text></g>')
    out.append('</svg>'); return ''.join(out)


def wrap_text(value, max_units=42, max_lines=2):
    import unicodedata
    lines=[]; line=''; units=0
    for c in ' '.join(str(value).split()):
        width=2 if unicodedata.east_asian_width(c) in ('W','F') else 1
        if units+width>max_units:
            lines.append(line);line='';units=0
        line+=c; units+=width
    if line: lines.append(line)
    if len(lines)>max_lines:
        lines=lines[:max_lines];lines[-1]=lines[-1][:-1]+'…'
    return lines


def project_svg(repo, theme='light'):
    p=PALETTES[theme]
    out=[svg_open(420,160,repo['name']+' — '+repo['description']),f'<rect x="1" y="1" width="418" height="158" rx="10" fill="{p["paper"]}" stroke="{p["edge"]}"/>']
    def text(x,y,s,size=15,color='ink'):
        out.append(f'<text x="{x}" y="{y}" fill="{p[color]}" font-size="{size}" font-family="Segoe UI,Microsoft YaHei,sans-serif">{escape(str(s))}</text>')
    title=wrap_text(repo['name'],30,1)[0]
    text(20,30,'KOUZI IS EXPLORING',10,'accent');text(20,57,title,20)
    for i,line in enumerate(wrap_text(repo['description'])): text(20,82+i*19,line,14,'muted')
    text(20,135,repo['language']+' · '+repo['updated_on']+' 更新',12,'accent');text(387,32,'↗',19,'accent')
    out.append('</svg>');return ''.join(out)
