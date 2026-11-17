"""Build Kouzi's public profile from GitHub. Python 3.11+, standard library only.

No network writes. All API calls finish and validate before local files change.
Never pass a token as a command-line argument or store one in generated files.
"""
from __future__ import annotations

import argparse
import base64
from datetime import date, datetime, timedelta, timezone
from html import escape
import hashlib
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

from pet_art import footprint_svg, garden_svg, passport_svg, project_svg, room_svg

ROOT = Path(__file__).resolve().parent.parent
API = 'https://api.github.com'
GRAPHQL = '''query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}'''
YEAR_QUERY = '''query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
      commitContributionsByRepository(maxRepositories: 100) {
        repository { nameWithOwner url isPrivate }
        contributions(last: 100) { nodes { occurredAt commitCount } }
      }
      issueContributions(last: 30) {
        nodes { occurredAt issue { title url repository { nameWithOwner isPrivate } } }
      }
      pullRequestContributions(last: 30) {
        nodes { occurredAt pullRequest { title url repository { nameWithOwner isPrivate } } }
      }
      repositoryContributions(last: 30) {
        nodes { occurredAt repository { nameWithOwner url isPrivate } }
      }
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
    return '长期室友' if level>=6 else '老朋友' if level>=4 else '常住客' if level>=2 else '新住客'


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
        description=clean(repo.get('description')) or f'{language} 项目，暂无简介。'
        name=clean(repo['name'],100)
        result.append(dict(name=name,url=f'https://github.com/{config["username"]}/{urllib.parse.quote(name,safe="")}',description=description,language=language,updated_on=(repo.get('pushed_at') or '')[:10],featured=config.get('featured_topic','kouzi-featured') in repo.get('topics',[])))
    return result


def fetch_raw_repositories(config, token):
    repos=[]
    for page in range(1,101):
        batch=api_json(f'/users/{config["username"]}/repos?per_page=100&sort=pushed&type=owner&page={page}',token)
        if not isinstance(batch,list): raise ProfileError('Unexpected GitHub repositories response.')
        repos.extend(batch)
        if len(batch)<100:
            return [r for r in repos if not r.get('private') and r.get('owner',{}).get('login','').lower()==config['username'].lower()]
    raise ProfileError('Repository pagination exceeded the supported limit; no partial list was published.')


def fetch_projects(config, token):
    return select_projects(fetch_raw_repositories(config,token),config)


def repository_library(raw, config, token):
    result=[]
    for repo in raw:
        if repo.get('private') or repo.get('owner',{}).get('login','').lower()!=config['username'].lower():continue
        name=clean(repo['name'],100)
        item={'name':name,'url':f'https://github.com/{config["username"]}/{urllib.parse.quote(name,safe="")}',
              'description':clean(repo.get('description')) or f'{clean(repo.get("language")) or "新"}项目，暂无简介。',
              'language':clean(repo.get('language'),40) or '尚未标注',
              'updated_on':(repo.get('pushed_at') or repo.get('updated_at') or '')[:10],
              'stars':repo.get('stargazers_count',0),'forks':repo.get('forks_count',0),
              'archived':bool(repo.get('archived')),'fork':bool(repo.get('fork')),
              'topics':[clean(t,50) for t in repo.get('topics',[])],
              'featured':config.get('featured_topic','kouzi-featured') in repo.get('topics',[])}
        # An automatic plain-text synopsis is enough for the profile; never copy a whole README.
        if not repo.get('description') and name.lower()!=config['username'].lower():
            try:
                document=api_json(f'/repos/{config["username"]}/{urllib.parse.quote(name,safe="")}/readme',token)
                if document.get('encoding')=='base64':
                    body=base64.b64decode(document.get('content','')).decode('utf-8',errors='replace')
                    item['description']=readme_synopsis(body) or item['description']
            except ProfileError as exc:
                if 'HTTP 404' not in str(exc):raise
        result.append(item)
    result.sort(key=lambda r:(r['featured'],r['updated_on'],r['name'].lower()),reverse=True)
    return result


def readme_synopsis(body):
    """Extract a short readable heading/paragraph, never execute Markdown or HTML."""
    heading='';paragraph=[];fenced=False
    for raw in body[:24000].splitlines():
        line=raw.strip()
        if line.startswith(('```','~~~')):
            if paragraph:break
            fenced=not fenced;continue
        if fenced:continue
        if not line:
            if paragraph:break
            continue
        if line.startswith(('<','![','[!','|','>','- ','* ')):continue
        line=re.sub(r'!\[[^\]]*\]\([^)]*\)','',line)
        line=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',line)
        line=re.sub(r'https?://\S+','',line)
        line=line.replace('**','').replace('`','').strip()
        if line.startswith('#'):
            if paragraph:break
            if not heading:heading=line.lstrip('#').strip()
            continue
        if line:paragraph.append(line)
        if sum(map(len,paragraph))>=180:break
    return clean(' · '.join(filter(None,(heading,' '.join(paragraph)))),180)


def parse_year(collection, today):
    try:
        calendar=collection['contributionCalendar']
        days=[]
        for week in calendar['weeks']:
            for day in week['contributionDays']:
                d=date.fromisoformat(day['date']);count=day['contributionCount']
                if not isinstance(count,int) or isinstance(count,bool) or count<0:raise ValueError('count')
                if d<=today:days.append({'date':d.isoformat(),'count':count})
        days.sort(key=lambda d:d['date'])
        dates=[date.fromisoformat(d['date']) for d in days]
        if not 360<=len(days)<=380 or len(set(dates))!=len(dates):raise ValueError('range')
        if dates[-1]!=today or (dates[-1]-dates[0]).days+1!=len(days):raise ValueError('missing dates')
        total=calendar['totalContributions']
        if not isinstance(total,int) or total<0:raise ValueError('total')
    except (KeyError,TypeError,ValueError,IndexError):
        raise ProfileError('Yearly calendar is incomplete or malformed; existing data was kept.') from None
    return {'total':total,'active_days':sum(d['count']>0 for d in days),'start':days[0]['date'],'end':days[-1]['date'],'days':days}


def activity_from_contributions(collection):
    """Public contribution history, independent of the short-lived Events feed."""
    entries=[]
    for group in collection.get('commitContributionsByRepository',[]):
        repo=group['repository']
        if repo.get('isPrivate',True):continue
        for node in group['contributions']['nodes']:
            entries.append({'date':node['occurredAt'][:10],'kind':'commit','repo':clean(repo['nameWithOwner'],150),'count':node['commitCount'],'title':f'完成了 {node["commitCount"]} 次提交'})
    for key,child,kind,label in (('issueContributions','issue','issue','提出了 Issue'),('pullRequestContributions','pullRequest','pr','发起了 Pull Request'),('repositoryContributions','repository','create','开始了新项目')):
        for node in collection.get(key,{}).get('nodes',[]):
            value=node[child];repo=value if child=='repository' else value['repository']
            if repo.get('isPrivate',True):continue
            entries.append({'date':node['occurredAt'][:10],'kind':kind,'repo':clean(repo['nameWithOwner'],150),'count':1,'title':label+(('：'+clean(value.get('title'),200)) if child!='repository' else '')})
    return sorted(entries,key=lambda e:(e['date'],e['kind']=='commit',e['repo']),reverse=True)[:60]


def fetch_year(config, token, today):
    result=api_json('/graphql',token,{'query':YEAR_QUERY,'variables':{'login':config['username']}})
    try:collection=result['data']['user']['contributionsCollection']
    except (KeyError,TypeError):raise ProfileError('GitHub did not return the yearly calendar.') from None
    return parse_year(collection,today),activity_from_contributions(collection)


def fetch_organizations(config, token):
    organizations=[]
    for page in range(1,101):
        rows=api_json(f'/users/{config["username"]}/orgs?per_page=100&page={page}',token)
        if not isinstance(rows,list):raise ProfileError('GitHub did not return public organizations.')
        organizations.extend({'login':clean(r['login'],100),'description':clean(r.get('description'),180),'url':'https://github.com/'+urllib.parse.quote(r['login'],safe='')} for r in rows)
        if len(rows)<100:return organizations
    raise ProfileError('Public organization pagination exceeded the supported limit.')


def fetch_days(config, ledger, token, now, seed=None):
    today=now.date()
    adopted=date.fromisoformat(config['adopted_on'])
    synced=date.fromisoformat(ledger.get('synced_through',config['adopted_on']))
    start=min(max(adopted,synced-timedelta(days=35)),today-timedelta(days=6))
    all_days={}
    seed=seed or {}
    while start<=today:
        end=min(today,start+timedelta(days=364))
        to_value=now.isoformat().replace('+00:00','Z') if end==today else end.isoformat()+'T23:59:59Z'
        payload={'query':GRAPHQL,'variables':{'login':config['username'],'from':start.isoformat()+'T00:00:00Z','to':to_value}}
        expected={ (start+timedelta(days=i)).isoformat() for i in range((end-start).days+1) }
        if expected.issubset(seed):
            all_days.update({d:seed[d] for d in expected});start=end+timedelta(days=1);continue
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
    status='窗边休息' if count==0 else '待在桌边' if count<=3 else '摆弄毛线' if count<=9 else '占着键盘'
    unlocks=['纸箱与小碗']
    for threshold,label in ((2,'地毯、毛线球与绿植'),(4,'窗边坐垫'),(6,'墙上挂画')):
        if level>=threshold:unlocks.append(label)
    return {'schema_version':3,'username':config['username'],'pet':{'name':config['pet_name'],'adopted_on':config['adopted_on'],'level':level,'title':level_title(level),'total_xp':total,'xp_in_level':total%60,'xp_to_next':60-total%60,'action':action,'status':status,'unlocks':unlocks},'today':{'date':today.isoformat(),'contributions':count,'earned_xp':ledger['days'].get(today.isoformat(),{}).get('xp',0)},'week':week,'projects':projects,'source':source,'updated_on':today.isoformat(),'calendar_basis':'GitHub 贡献日历日期（UTC）；GitHub 可能延迟计入贡献。'}


def enrich_playfulness(model, ledger):
    """Summarize room tenure and milestones from real saved progress."""
    today=date.fromisoformat(model['updated_on'])
    adopted=date.fromisoformat(model['pet']['adopted_on'])
    days_together=(today-adopted).days+1
    active_days=sum(item['xp']>0 for item in ledger['days'].values())
    library=[r for r in model.get('repositories',[]) if r['name'].lower()!=model['username'].lower() and not r.get('fork') and not r.get('archived')]
    languages=sorted({r['language'] for r in library if r['language']!='尚未标注'})
    milestones=(('入住','开始记录',True),('起步','累计 5 XP',model['pet']['total_xp']>=5),('活跃 · 3 天','领养后累计 3 个活跃日',active_days>=3),('活跃 · 7 天','领养后累计 7 个活跃日',active_days>=7),('项目 · 3 个','拥有 3 个公开原创项目',len(library)>=3),('Lv.2','累计 60 XP',model['pet']['level']>=2))
    model['scrapbook']={'days_together':days_together,'active_days':active_days,'languages':languages,
                        'stamps':[{'name':name,'requirement':rule,'unlocked':unlocked} for name,rule,unlocked in milestones]}
    return model


def picture(base, alt, width=900, revision=''):
    suffix='?v='+revision if revision else ''
    return f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="./assets/{base}-dark.svg{suffix}">\n  <img src="./assets/{base}-light.svg{suffix}" alt="{escape(alt,quote=True)}" width="{width}">\n</picture>'


def render_readme(model):
    pet=model['pet'];name=md_text(pet['name']);book=model.get('scrapbook',{})
    revision=hashlib.sha256(dump(model).encode()).hexdigest()[:12]
    def image(base,alt,width=900):return picture(base,alt,width,revision)
    lines=[f'# William & {name}', '', '个人项目与开发记录，外加一只叫 **'+name+'** 的猫。', '',
           image('kouzi-room',pet['status'],900), '', image('kouzi-passport','扣子的成长记录',900), '',
           '## 近七天', '', image('kouzi-footprints','近七天贡献',630), '',
           f'今日贡献 **{model["today"]["contributions"]}** · 今日经验 **{model["today"]["earned_xp"]} XP**', '',
           '<details>', '<summary>全年贡献</summary>', '',
           image('kouzi-garden','全年贡献：每格一天，颜色越深贡献越多',900), '',
           '每格一天，颜色越深贡献越多。日期详情可在下方 GitHub 贡献区查看。', '', '</details>', '',
           '## 成长记录', '', '| 里程碑 | 条件 | 状态 |', '| :--- | :--- | :--- |']
    for stamp in book.get('stamps',[]):
        lines.append(f'| {md_text(stamp["name"])} | {md_text(stamp["requirement"])} | {"已达成" if stamp["unlocked"] else "未达成"} |')
    lines.extend(['', '## 项目', ''])
    for i,repo in enumerate(model['projects']):
        lines.extend([image(f'project-{i+1}',repo['name']+'：'+repo['description'],450),''])
    lines.extend(['<details>', '<summary>全部公开仓库与常用语言</summary>', '', '| 项目 | 技术 | 最近推送 | 简介 |', '| :--- | :--- | :--- | :--- |'])
    for repo in model.get('repositories',[]):
        lines.append(f'| {md_text(repo["name"])} | {md_text(repo["language"])} | {repo["updated_on"]} | {md_text(repo["description"])} |')
    lines.extend(['', '**常用语言**：'+(' · '.join(md_text(s) for s in book.get('languages',[])) or '暂无数据'), '', '</details>', '',
                  '## 最近活动', '', '| 日期 | 活动 |', '| :--- | :--- |'])
    entries=model.get('activity',[])
    for entry in entries[:5]:
        lines.append(f'| {entry["date"]} | {md_text(entry["repo"])} · {md_text(entry["title"])} |')
    if not entries:lines.append('| — | 暂无公开活动 |')
    if len(entries)>5:
        lines.extend(['', '<details>', '<summary>更早的活动</summary>', '', '| 日期 | 活动 |', '| :--- | :--- |'])
        for entry in entries[5:20]:lines.append(f'| {entry["date"]} | {md_text(entry["repo"])} · {md_text(entry["title"])} |')
        lines.extend(['', '</details>'])
    lines.extend(['', '<details>', '<summary>成长规则与房间变化</summary>', '',
                  'GitHub 每日贡献会自动结算：0 次 → 0 XP，1–3 次 → 5 XP，4–9 次 → 8 XP，10 次以上 → 10 XP。每 60 XP 升一级，领养前的历史不补发经验；休息不扣分。', '',
                  '| 等级 | 房间变化 |', '| :--- | :--- |', '| Lv.1 | 纸箱与小碗 |', '| Lv.2 | 地毯、毛线球与绿植 |', '| Lv.4 | 窗边坐垫 |', '| Lv.6 | 墙上挂画 |', '',
                  '当前已解锁：'+md_text('；'.join(pet['unlocks']))+'。', '', '</details>', '',
                  '<details>', '<summary>数据与更新说明</summary>', '',
                  '每天自动同步公开仓库和贡献记录。GitHub 数据可能延迟，与登录后看到的统计可能不同。项目摘要优先取自仓库简介，再从 README 提取。', '', '</details>', '',
                  f'<sub>领养于 {pet["adopted_on"]} · 更新于 {model["updated_on"]} · 每日同步</sub>', ''])
    return '\n'.join(lines)


def md_text(value):
    """Treat repository metadata as text, including inside GFM table cells."""
    value=clean(value,500)
    # Encode punctuation that could create Markdown links, tags, tables or mentions.
    return ''.join(f'&#{ord(c)};' if c in '&<>|`*_[]!\\@' else c for c in value)


def build_files(model, ledger):
    files={'README.md':render_readme(model),'data/growth.json':dump(ledger),'data/profile.json':dump(model)}
    pet=model['pet']
    for theme in ('light','dark'):
        files[f'assets/kouzi-room-{theme}.svg']=room_svg(theme,pet['action'],pet['level'],pet['name'])
        files[f'assets/kouzi-footprints-{theme}.svg']=footprint_svg(model['week'],theme)
        files[f'assets/kouzi-passport-{theme}.svg']=passport_svg(model,theme)
        files[f'assets/kouzi-garden-{theme}.svg']=garden_svg(model.get('calendar',{}),theme)
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
    raw_repos=fetch_raw_repositories(config,token)
    projects=select_projects(raw_repos,config)
    year,activity=fetch_year(config,token,today)
    counts=fetch_days(config,previous,token,now,seed={d['date']:d['count'] for d in year['days']})
    organizations=fetch_organizations(config,token)
    repositories=repository_library(raw_repos,config,token)
    descriptions={r['name']:r['description'] for r in repositories}
    for project in projects:project['description']=descriptions.get(project['name'],project['description'])
    ledger=advance_growth(previous,counts,config,today)
    model=model_from(config,ledger,counts,projects,today)
    model.update({'calendar':year,'activity':activity,'organizations':organizations,'repositories':repositories,
                  'public_stats':{'repositories':len(repositories),'stars':sum(r['stars'] for r in repositories)},
                  'visibility_note':'公开数据视角；与你登录后看到的私有贡献及组织信息可能不同。'})
    enrich_playfulness(model,ledger)
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
