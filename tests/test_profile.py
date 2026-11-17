"""Regression coverage for real growth accounting, API failure safety, and public data."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update_profile as p

CONFIG={'username':'William-331','pet_name':'扣子','adopted_on':'2026-11-17','xp_per_level':60,'project_limit':4,'featured_topic':'kouzi-featured','excluded_repos':[],'pages_url':'https://william-331.github.io/William-331/','experience_url':'https://william-331.github.io/'}
TODAY=date(2026,11,17)


def repo(name, **changes):
    result={'name':name,'owner':{'login':'William-331'},'private':False,'fork':False,'archived':False,'size':10,'topics':[],'language':'Python','pushed_at':'2026-11-17T12:00:00Z','description':None}
    result.update(changes);return result


class GrowthTests(unittest.TestCase):
    def test_daily_thresholds_and_cap(self):
        self.assertEqual([p.daily_xp(n) for n in (0,1,3,4,9,10,9999)],[0,5,5,8,8,10,10])
        with self.assertRaises(ValueError):p.daily_xp(-1)

    def test_same_day_rerun_and_tier_increase_do_not_double_count(self):
        initial=p.advance_growth({}, {'2026-11-17':2}, CONFIG,TODAY)
        self.assertEqual(initial,p.advance_growth(initial,{'2026-11-17':2},CONFIG,TODAY))
        higher=p.advance_growth(initial,{'2026-11-17':20},CONFIG,TODAY)
        self.assertEqual(higher['days']['2026-11-17']['xp'],10)
        self.assertEqual(initial['days']['2026-11-17']['xp'],5)

    def test_rest_or_revised_counts_never_remove_earned_xp(self):
        initial=p.advance_growth({}, {'2026-11-17':10}, CONFIG,TODAY)
        revised=p.advance_growth(initial,{'2026-11-17':0,'2026-11-18':0},CONFIG,TODAY+timedelta(days=1))
        self.assertEqual(sum(d['xp'] for d in revised['days'].values()),10)

    def test_only_adopted_dates_are_awarded_and_late_data_is_backfilled(self):
        initial=p.advance_growth({}, {'2026-11-16':99,'2026-11-17':0,'2026-11-19':99}, CONFIG,TODAY)
        self.assertEqual(set(initial['days']),{'2026-11-17'})
        late=p.advance_growth(initial,{'2026-11-17':4,'2026-11-18':0},CONFIG,TODAY+timedelta(days=1))
        self.assertEqual(late['days']['2026-11-17']['xp'],8)

    def test_adoption_date_cannot_silently_reset_progress(self):
        initial=p.advance_growth({}, {'2026-11-17':1}, CONFIG,TODAY)
        with self.assertRaises(p.ProfileError):p.advance_growth(initial,{},dict(CONFIG,adopted_on='2026-11-18'),TODAY)

    def test_growth_milestones(self):
        counts={(TODAY-timedelta(days=i)).isoformat():0 for i in range(7)}
        for total,level,title in ((0,1,'初来乍到'),(60,2,'键盘学徒'),(180,4,'代码搭子'),(300,6,'仓库守护猫')):
            ledger={'days':{str(i):{'xp':10} for i in range(total//10)}}
            model=p.model_from(CONFIG,ledger,counts,[],TODAY)
            self.assertEqual((model['pet']['level'],model['pet']['title']),(level,title))
            self.assertEqual(model['pet']['xp_in_level'],0)
            if level==6:self.assertIn('仓库守护猫纪念画',model['pet']['unlocks'])


class ProjectsTests(unittest.TestCase):
    def test_excludes_private_fork_archived_empty_self_and_other_owner(self):
        repos=[repo('valid'),repo('secret',private=True),repo('fork',fork=True),repo('archive',archived=True),repo('empty',size=0),repo('William-331'),repo('other',owner={'login':'other'})]
        self.assertEqual([r['name'] for r in p.select_projects(repos,CONFIG)],['valid'])

    def test_featured_then_push_recency_and_missing_description(self):
        repos=[repo('old',pushed_at='2026-01-01T00:00:00Z'),repo('new'),repo('favorite',pushed_at='2025-01-01T00:00:00Z',topics=['kouzi-featured'])]
        selected=p.select_projects(repos,CONFIG)
        self.assertEqual([r['name'] for r in selected],['favorite','new','old'])
        self.assertIn('Python',selected[0]['description'])

    def test_all_repository_pages_are_considered(self):
        page=[repo('r'+str(i)) for i in range(100)]
        with patch.object(p,'api_json',side_effect=[page,[repo('featured',topics=['kouzi-featured'])]]) as mocked:
            selected=p.fetch_projects(CONFIG,'not-a-real-token')
        self.assertEqual(mocked.call_count,2)
        self.assertEqual(selected[0]['name'],'featured')


class ReliabilityTests(unittest.TestCase):
    def test_incomplete_calendar_is_an_error_not_zero_xp(self):
        response={'data':{'user':{'contributionsCollection':{'contributionCalendar':{'weeks':[]}}}}}
        with patch.object(p,'api_json',return_value=response):
            with self.assertRaises(p.ProfileError):p.fetch_days(CONFIG,{},'not-a-real-token',datetime(2026,11,17,12,tzinfo=timezone.utc))

    def test_api_failure_preserves_every_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir()
            (root/'profile.config.json').write_text(json.dumps(CONFIG),encoding='utf-8')
            (root/'README.md').write_text('existing profile',encoding='utf-8')
            (root/'data/growth.json').write_text(json.dumps({'adopted_on':'2026-11-17','days':{}}),encoding='utf-8')
            before={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
            with patch.object(p,'get_token',return_value='not-a-real-token'),patch.object(p,'fetch_raw_repositories',side_effect=p.ProfileError('API unavailable')):
                with self.assertRaises(p.ProfileError):p.run(root)
            after={str(f.relative_to(root)):f.read_bytes() for f in root.rglob('*') if f.is_file()}
            self.assertEqual(before,after)

    def test_generated_svg_escapes_untrusted_repo_metadata(self):
        counts={(TODAY-timedelta(days=i)).isoformat():i for i in range(7)}
        ledger=p.advance_growth({},counts,CONFIG,TODAY)
        projects=p.select_projects([repo('test',description='<script>alert("x")</script> & <foreignObject>')],CONFIG)
        model=p.model_from(CONFIG,ledger,counts,projects,TODAY)
        files=p.build_files(model,ledger)
        for path,content in files.items():
            if path.endswith('.svg'):
                node=ET.fromstring(content)
                self.assertFalse(any(e.tag.endswith('script') or e.tag.endswith('foreignObject') for e in node.iter()))
        self.assertNotIn('<script>',files['site/data.js'])


class IntegratedHomeTests(unittest.TestCase):
    def year_collection(self):
        days=[{'date':(TODAY-timedelta(days=i)).isoformat(),'contributionCount':1 if i%7==0 else 0} for i in range(364,-1,-1)]
        return {'contributionCalendar':{'totalContributions':sum(d['contributionCount'] for d in days),'weeks':[{'contributionDays':days}]}}

    def test_year_calendar_is_complete_and_does_not_award_pre_adoption_xp(self):
        calendar=p.parse_year(self.year_collection(),TODAY)
        self.assertEqual(len(calendar['days']),365)
        self.assertEqual(calendar['total'],53)
        growth=p.advance_growth({},dict((d['date'],d['count']) for d in calendar['days']),CONFIG,TODAY)
        self.assertEqual(set(growth['days']),{'2026-11-17'})
        self.assertEqual(growth['days']['2026-11-17']['xp'],5)

    def test_year_missing_day_or_duplicate_is_rejected(self):
        collection=self.year_collection()
        days=collection['contributionCalendar']['weeks'][0]['contributionDays']
        del days[123]
        with self.assertRaises(p.ProfileError):p.parse_year(collection,TODAY)
        collection=self.year_collection()
        days=collection['contributionCalendar']['weeks'][0]['contributionDays']
        days[123]=dict(days[124])
        with self.assertRaises(p.ProfileError):p.parse_year(collection,TODAY)

    def test_recent_activity_filters_private_repositories_and_sorts_dates(self):
        def group(name,private,day):
            return {'repository':{'nameWithOwner':name,'isPrivate':private},'contributions':{'nodes':[{'occurredAt':day+'T00:00:00Z','commitCount':2}]}}
        collection={'commitContributionsByRepository':[group('William-331/private',True,'2026-11-17'),group('William-331/old',False,'2026-07-17'),group('William-331/new',False,'2026-11-17')]}
        result=p.activity_from_contributions(collection)
        self.assertEqual([r['repo'] for r in result],['William-331/new','William-331/old'])
        self.assertNotIn('private',json.dumps(result))

    def test_repository_notes_stay_public_and_are_size_limited(self):
        import base64
        content='<script>untrusted()</script>\n'+'x'*25000
        response={'encoding':'base64','content':base64.b64encode(content.encode()).decode()}
        with patch.object(p,'api_json',return_value=response) as mocked:
            result=p.repository_library([repo('private',private=True),repo('public')],CONFIG,'test')
        self.assertEqual(mocked.call_count,1)
        self.assertEqual([r['name'] for r in result],['public'])
        self.assertTrue(result[0]['readme_truncated'])
        self.assertEqual(len(result[0]['readme']),24000)

    def test_year_seed_avoids_redundant_calendar_requests(self):
        calendar=p.parse_year(self.year_collection(),TODAY)
        with patch.object(p,'api_json',side_effect=AssertionError('Unexpected extra request')):
            counts=p.fetch_days(CONFIG,{},'test',datetime(2026,11,17,12,tzinfo=timezone.utc),seed={d['date']:d['count'] for d in calendar['days']})
        self.assertEqual(len(counts),7)
        self.assertEqual(counts[TODAY.isoformat()],1)


if __name__=='__main__':unittest.main()
