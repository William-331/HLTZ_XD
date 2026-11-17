"""Build Kouzi's public profile from GitHub. Python 3.11+, standard library only.

No network writes. All API calls finish and validate before local files change.
Never pass a token as a command-line argument or store one in generated files.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from pet_art import footprint_svg, project_svg, room_svg

ROOT = Path(__file__).resolve().parent.parent
API = 'https://api.github.com'
GRAPHQL = '''query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}'''


class ProfileError(Exception):
    pass


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def clean(value, limit=300):
    return ''.join(c for c in str(value or '') if ord(c)>=32).strip()[:limit]


def validate_config(config):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', config.get('username','')):
        raise ProfileError('Invalid GitHub username in profile.config.json.')
    date.fromisoformat(config['adopted_on'])
    if config.get('xp_per_level') != 60:
        raise ProfileError('xp_per_level must remain 60 to keep earned levels stable.')
    if not 1 <= config.get('project_limit',0) <= 12:
        raise ProfileError('project_limit must be 1–12.')
    if not clean(config.get('pet_name')):
        raise ProfileError('pet_name is required.')
    for key in ('pages_url','experience_url'):
        if not config.get(key,'').startswith('https://'):
            raise ProfileError(f'{key} must use HTTPS.')


def get_token(use_git_credential=False):
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token and use_git_credential:
        env={**os.environ,'GIT_TERMINAL_PROMPT':'0','GCM_INTERACTIVE':'never'}
        result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',capture_output=True,text=True,timeout=20,env=env)
        fields=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
        token=fields.get('password')
    if not token:
        raise ProfileError('GitHub token missing. In Actions use github.token; locally set GH_TOKEN or use --use-git-credential. No files were changed.')
    return token


def api_json(path, token, payload=None):
    url=path if path.startswith(API+'/') else API+path
    headers={'User-Agent':'Kouzi-Profile/1.0','Accept':'application/vnd.github+json','Authorization':'Bearer '+token,'X-GitHub-Api-Version':'2022-11-28'}
    body=None
    if payload is not None:
        body=json.dumps(payload).encode('utf-8');headers['Content-Type']='application/json'
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers=headers,data=body)
            with urllib.request.urlopen(request,timeout=25) as response:
                result=json.load(response)
            if isinstance(result,dict) and result.get('errors'):
                raise ProfileError('GitHub GraphQL rejected the query. Check token access and API availability. No files were changed.')
            return result
        except urllib.error.HTTPError as exc:
            if exc.code in (429,500,502,503,504) and attempt<2:
                time.sleep(1+attempt);continue
            raise ProfileError(f'GitHub HTTP {exc.code}. Previous profile and growth data have been kept.') from None
        except (urllib.error.URLError,TimeoutError,ConnectionError):
            if attempt<2:
                time.sleep(1+attempt);continue
            raise ProfileError('GitHub connection failed. Previous profile and growth data have been kept.') from None
    raise ProfileError('GitHub request did not complete.')


def daily_xp(count):
    if count < 0:
        raise ValueError('Contribution counts cannot be negative.')
    return 0 if count==0 else 5 if count<=3 else 8 if count<=9 else 10


def level_title(level):
    return '仓库守护猫' if level>=6 else '代码搭子' if level>=4 else '键盘学徒' if level>=2 else '初来乍到'


def select_projects(repos, config):
    excluded={name.lower() for name in config.get('excluded_repos',[])}
    excluded.add(config['username'].lower())
    selected=[]
    for repo in repos:
        if (repo.get('private') or repo.get('fork') or repo.get('archived') or repo.get('disabled')
            or not repo.get('size') or repo.get('name','').lower() in excluded
            or repo.get('owner',{}).get('login','').lower()!=config['username'].lower()):
            continue
        selected.append(repo)
    selected.sort(key=lambda r: (config.get('featured_topic','kouzi-featured') in r.get('topics',[]),r.get('pushed_at') or '',r.get('name','').lower()),reverse=True)
    result=[]
    for repo in selected[:config['project_limit']]:
        language=clean(repo.get('language'),40) or '多种技术'
        description=clean(repo.get('description')) or f'{language} 项目，扣子正在研究中。'
        name=clean(repo['name'],100)
        result.append(dict(name=name,url=f'https://github.com/{config["username"]}/{urllib.parse.quote(name,safe="")}',description=description,language=language,updated_on=(repo.get('pushed_at') or '')[:10],featured=config.get('featured_topic','kouzi-featured') in repo.get('topics',[])))
    return result


def fetch_projects(config, token):
    repos=[]
    for page in range(1,101):
        batch=api_json(f'/users/{config["username"]}/repos?per_page=100&sort=pushed&type=owner&page={page}',token)
        if not isinstance(batch,list): raise ProfileError('Unexpected GitHub repositories response.')
        repos.extend(batch)
        if len(batch)<100: return select_projects(repos,config)
    raise ProfileError('Repository pagination exceeded the supported limit; no partial list was published.')


def fetch_days(config, ledger, token, now):
    today=now.date()
    adopted=date.fromisoformat(config['adopted_on'])
    synced=date.fromisoformat(ledger.get('synced_through',config['adopted_on']))
    start=min(max(adopted,synced-timedelta(days=35)),today-timedelta(days=6))
    all_days={}
    while start<=today:
        end=min(today,start+timedelta(days=364))
        to_value=now.isoformat().replace('+00:00','Z') if end==today else end.isoformat()+'T23:59:59Z'
        payload={'query':GRAPHQL,'variables':{'login':config['username'],'from':start.isoformat()+'T00:00:00Z','to':to_value}}
        result=api_json('/graphql',token,payload)
        try:
            weeks=result['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
            for week in weeks:
                for item in week['contributionDays']:
                    day=date.fromisoformat(item['date'])
                    count=item['contributionCount']
                    if not isinstance(count,int) or isinstance(count,bool) or count<0: raise ValueError('Invalid count')
                    if start<=day<=end: all_days[day.isoformat()]=count
        except (KeyError,TypeError,ValueError):
            raise ProfileError('GitHub contribution data was incomplete or malformed; no files were changed.') from None
        expected={ (start+timedelta(days=i)).isoformat() for i in range((end-start).days+1) }
        if not expected.issubset(all_days):
            raise ProfileError('GitHub omitted contribution dates; no missing dates were silently treated as zero.')
        start=end+timedelta(days=1)
    return all_days


def advance_growth(previous, days, config, today):
    adopted=date.fromisoformat(config['adopted_on'])
    if previous and previous.get('adopted_on')!=config['adopted_on']:
        raise ProfileError('adopted_on changed. Restore its original value to preserve the growth ledger.')
    ledger=json.loads(json.dumps(previous)) if previous else {'version':1,'adopted_on':config['adopted_on'],'days':{}}
    for day,count in sorted(days.items()):
        d=date.fromisoformat(day)
        if not adopted<=d<=today: continue
        old=ledger['days'].get(day,{'xp':0})
        # Replace a day's record, never append another award for a repeated run.
        # Earned XP is retained even if GitHub later revises/deletes contributions.
        ledger['days'][day]={'contributions':count,'xp':max(old['xp'],daily_xp(count))}
    ledger['synced_through']=today.isoformat()
    return ledger


def model_from(config, ledger, counts, projects, today, source='github'):
    total=sum(item['xp'] for item in ledger['days'].values())
    level=1+total//60
    week=[{'date':(today-timedelta(days=offset)).isoformat(),'count':counts[(today-timedelta(days=offset)).isoformat()]} for offset in range(6,-1,-1)]
    count=counts[today.isoformat()]
    action='sleep' if count==0 else 'idle' if count<=3 else 'play'
    status='今天在晒太阳，等你回家' if count==0 else '吃饱了，正在陪你写代码' if count<=3 else '精神很好，和毛线球搏斗中' if count<=9 else '认真监工模式已开启'
    unlocks=['纸箱与小碗']
    for threshold,label in ((2,'猫窝、毛线球与绿植'),(4,'窗边坐垫'),(6,'仓库守护猫纪念画')):
        if level>=threshold:unlocks.append(label)
    return {'schema_version':1,'username':config['username'],'pet':{'name':config['pet_name'],'adopted_on':config['adopted_on'],'level':level,'title':level_title(level),'total_xp':total,'xp_in_level':total%60,'xp_to_next':60-total%60,'action':action,'status':status,'unlocks':unlocks},'today':{'date':today.isoformat(),'contributions':count,'earned_xp':ledger['days'].get(today.isoformat(),{}).get('xp',0)},'week':week,'projects':projects,'pages_url':config['pages_url'],'experience_url':config['experience_url'],'source':source,'updated_on':today.isoformat(),'calendar_basis':'GitHub 贡献日历日期（UTC）；GitHub 可能延迟计入贡献。'}


def picture(base, alt, width=900):
    return f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="./assets/{base}-dark.svg">\n  <img src="./assets/{base}-light.svg" alt="{escape(alt,quote=True)}" width="{width}">\n</picture>'


def render_readme(model):
    pet=model['pet'];name=pet['name']
    lines=[f'# I build things. {name}负责监工。','',f'你好，我是 William。写点代码，也养一只叫 **{name}** 的小猫。','',picture('kouzi-room',f'{name}的像素猫窝：{pet["status"]}'),'',f'**{name} · Lv. {pet["level"]} {pet["title"]}**  ',f'{pet["status"]}。本级经验 **{pet["xp_in_level"]}/60 XP**，再攒 {pet["xp_to_next"]} XP 就能升级。','',f'[🐟 喂{name}](<{model["pages_url"]}?action=feed>) · [🧶 陪它玩](<{model["pages_url"]}?action=play>) · [🌙 一起休息](<{model["pages_url"]}?action=sleep>)','', '休息不掉级。你忙的时候，它就在家晒太阳。','',f'## {name}最近在研究什么','', '<!-- AUTO-GENERATED: repository metadata, never edit individual project cards. -->','']
    if model['projects']:
        lines.append('<p>')
        for i,repo in enumerate(model['projects']):
            lines.append(f'<a href="{escape(repo["url"],quote=True)}">{picture(f"project-{i+1}",repo["name"]+" — "+repo["description"],420)}</a>')
        lines.extend(['</p>',''])
    else:lines.extend(['小猫正在等第一个项目。公开、非 fork、未归档且非空的仓库会自动出现在这里。',''])
    lines.extend(['<sub>自动展示最近更新的项目；给仓库添加 `kouzi-featured` Topic 可优先展示。</sub>','','## 一起长大','',picture('kouzi-footprints','最近七天的贡献足迹；月亮代表休息，猫爪代表有贡献的一天',490),'',f'从 **{pet["adopted_on"]}** 开始一起生活，累计 **{pet["total_xp"]} XP**。  ', '**初来乍到** → **键盘学徒** → **代码搭子** → **仓库守护猫**','',f'已解锁：{"、".join(pet["unlocks"])}。','', '<details>','<summary>扣子是怎么长大的？</summary>','', '| 当日贡献数 | 经验 |','| --- | --- |','| 0 | 0 XP，安心休息 |','| 1–3 | 5 XP |','| 4–9 | 8 XP |','| 10 或更多 | 10 XP |','','每级 60 XP；每天最多 10 XP，同一天重复同步不会重复加分。贡献只从领养日起计入，已获得的经验不会因休息或后续贡献修订而扣除。','','等级 2 解锁猫窝、毛线球和绿植；等级 4 解锁窗边坐垫；等级 6 解锁纪念画。独立猫窝里的喂食和玩耍只改变本机互动状态，不增加真实经验。','','</details>','', f'<sub>数据同步：{model["updated_on"]} · 按 GitHub 贡献日历统计 · 每日自动更新，可能有延迟。</sub>','', f'[GitHub](https://github.com/{model["username"]}) · [去扣子家坐坐]({model["pages_url"]}) · [Interactive Experience]({model["experience_url"]})',''])
    if model['source']!='github':lines.insert(2,'> 演示数据：尚未连接 GitHub，不代表实际成长进度。\n')
    return '\n'.join(lines)


def build_files(model, ledger):
    files={'README.md':render_readme(model),'data/growth.json':dump(ledger),'data/profile.json':dump(model),'site/data.json':dump(model),'site/data.js':'window.KOUZI_PROFILE = '+json.dumps(model,ensure_ascii=False).replace('<','\\u003c')+';\n','site/.nojekyll':''}
    pet=model['pet']
    for theme in ('light','dark'):
        files[f'assets/kouzi-room-{theme}.svg']=room_svg(theme,pet['action'],pet['level'],pet['name'])
        files[f'assets/kouzi-footprints-{theme}.svg']=footprint_svg(model['week'],theme)
        for action in ('idle','feed','play','sleep'):
            files[f'site/assets/kouzi-{action}-{theme}.svg']=room_svg(theme,action,pet['level'],pet['name'])
        for i,repo in enumerate(model['projects']):files[f'assets/project-{i+1}-{theme}.svg']=project_svg(repo,theme)
    return files


def atomic_write_all(root, files):
    # Stage every output before replacing any file; network failures cannot create a half-empty profile.
    with tempfile.TemporaryDirectory(prefix='kouzi-',dir=root) as staging:
        for relative,content in files.items():
            target=Path(staging)/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content,encoding='utf-8',newline='\n')
        for relative in files:
            destination=root/relative;destination.parent.mkdir(parents=True,exist_ok=True);os.replace(Path(staging)/relative,destination)


def run(root=ROOT, use_git_credential=False):
    config=read_json(root/'profile.config.json');validate_config(config)
    now=datetime.now(timezone.utc);today=now.date()
    if date.fromisoformat(config['adopted_on'])>today:raise ProfileError('The adoption date is in the future.')
    ledger_path=root/'data/growth.json'
    previous=read_json(ledger_path) if ledger_path.exists() else {}
    token=get_token(use_git_credential)
    projects=fetch_projects(config,token)
    counts=fetch_days(config,previous,token,now)
    ledger=advance_growth(previous,counts,config,today)
    model=model_from(config,ledger,counts,projects,today)
    files=build_files(model,ledger)
    atomic_write_all(root,files)
    print(f'Updated {config["pet_name"]}: Lv. {model["pet"]["level"]}, {model["pet"]["total_xp"]} lifetime XP; {len(projects)} public projects. No secrets written.')
    return model


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--use-git-credential',action='store_true',help='Read an existing github.com credential from Git, without saving or printing it.')
    args=parser.parse_args()
    try:run(use_git_credential=args.use_git_credential)
    except (ProfileError,ValueError,KeyError,OSError,subprocess.TimeoutExpired) as exc:
        print('Kouzi update failed: '+clean(str(exc),400),file=sys.stderr);sys.exit(1)
