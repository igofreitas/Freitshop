import os,tempfile,unittest,sqlite3
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import visitor_tracking as visits

class VisitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=self.tmp.name+'/visits.db'
        self.env=patch.dict(os.environ,{'STATS_DB_PATH':self.path,'TRUSTED_PROXY_HOPS':'0','VISITOR_HASH_KEY':''});self.env.start()
        self.today=datetime(2026,10,25,12,tzinfo=timezone.utc)
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def test_once_per_day_and_next_day(self):
        self.assertEqual(visits.stats('203.0.113.9',self.today)['total'],1)
        self.assertEqual(visits.stats('203.0.113.9',self.today)['total'],1)
        self.assertEqual(visits.stats('203.0.113.10',self.today)['today'],2)
        result=visits.stats('203.0.113.9',datetime(2026,10,26,12,tzinfo=timezone.utc))
        self.assertEqual(result['today'],1);self.assertEqual(result['total'],3)
        db=sqlite3.connect(self.path)
        self.assertEqual(db.execute('SELECT DISTINCT day FROM daily_visitors').fetchall(),[('2026-10-26',)]);db.close()
        self.assertNotIn(b'203.0.113.9',Path(self.path).read_bytes())
    def test_atomic_dedup(self):
        with ThreadPoolExecutor(max_workers=12) as pool:list(pool.map(lambda _:visits.stats('203.0.113.9',self.today),range(60)))
        self.assertEqual(visits.stats(now=self.today)['total'],1)
    def test_ipv6_and_timezone(self):
        self.assertEqual(visits.canonical_ip('::ffff:203.0.113.9'),'203.0.113.9')
        self.assertEqual(visits.day_of(datetime(2026,10,26,2,59,tzinfo=timezone.utc)),'2026-10-25')
        self.assertEqual(visits.day_of(datetime(2026,10,26,3,0,tzinfo=timezone.utc)),'2026-10-26')
    def test_proxy_handling(self):
        self.assertEqual(visits.client_ip('192.0.2.1',{'X-Forwarded-For':'203.0.113.9'}),'192.0.2.1')
        with patch.dict(os.environ,{'TRUSTED_PROXY_HOPS':'1'}):
            self.assertEqual(visits.client_ip('192.0.2.1',{'X-Forwarded-For':'198.51.100.99,203.0.113.9'}),'203.0.113.9')
            with self.assertRaises(ValueError):visits.client_ip('192.0.2.1',{})
        with patch.dict(os.environ,{'TRUSTED_PROXY_HOPS':'2'}):
            self.assertEqual(visits.client_ip('192.0.2.1',{'X-Forwarded-For':'203.0.113.9,192.0.2.2'}),'203.0.113.9')
    def test_legacy_totals_not_mislabeled(self):
        db=sqlite3.connect(self.path);db.execute('CREATE TABLE views(day TEXT PRIMARY KEY,count INTEGER)');db.execute("INSERT INTO views VALUES('2026-10-24',500)");db.commit();db.close()
        self.assertEqual(visits.stats('203.0.113.9',self.today)['total'],1)
        db=sqlite3.connect(self.path);self.assertEqual(db.execute('SELECT count FROM views').fetchone()[0],500);db.close()

    def test_cookie_persistence_and_tampering(self):
        identity,cookie=visits.browser_identity('')
        self.assertIn('HttpOnly',cookie)
        self.assertEqual(visits.browser_identity(cookie.split(';')[0]),(identity,None))
        other,_=visits.browser_identity(cookie.split(';')[0]+'broken')
        self.assertNotEqual(identity,other)
