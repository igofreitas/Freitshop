import os,tempfile,unittest,threading,json,uuid,sqlite3
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import visitor_tracking as visits,postgres_counter as pg,server

class PostgreSQLRoutingTests(unittest.TestCase):
    def test_database_url_selects_postgres(self):
        with patch.dict(os.environ,{'DATABASE_URL':'postgresql://test'}),patch.object(pg,'stats',return_value={'total':42}) as call,patch.object(visits.sqlite3,'connect',side_effect=AssertionError('SQLite não permitido')):
            self.assertEqual(visits.stats('browser')['total'],42);call.assert_called_once()
    def test_database_failure_never_falls_back_or_exposes_credentials(self):
        with patch.dict(os.environ,{'DATABASE_URL':'postgresql://user:secret@127.0.0.1:1/db'}),patch.object(visits.sqlite3,'connect',side_effect=AssertionError('SQLite não permitido')):
            with self.assertRaises(pg.CounterStorageError) as error:visits.stats()
            self.assertNotIn('secret',str(error.exception))
    def test_http_error_and_home_survive_postgres_failure(self):
        with patch.dict(os.environ,{'DATABASE_URL':'postgresql://test'}),patch.object(pg,'connection',side_effect=pg.CounterStorageError('offline')):
            srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
            t=threading.Thread(target=srv.serve_forever,daemon=True);t.start();base='http://127.0.0.1:'+str(srv.server_port)
            try:
                for request in [base+'/api/stats',Request(base+'/api/visit',data=b'')]:
                    with self.assertRaises(HTTPError) as error:urlopen(request)
                    self.assertEqual(error.exception.code,503)
                with urlopen(base+'/') as r:self.assertEqual(r.status,200)
            finally:srv.shutdown();srv.server_close();t.join()

@unittest.skipUnless(os.environ.get('TEST_POSTGRES_URL'),'Defina TEST_POSTGRES_URL para integração PostgreSQL real.')
class PostgreSQLIntegrationTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.url=os.environ['TEST_POSTGRES_URL'];self.schema='test_counter_'+uuid.uuid4().hex
        self.original=psycopg.connect
        with self.original(self.url) as db:db.execute('CREATE SCHEMA '+self.schema)
        def connect(url,**kwargs):
            kwargs['options']=kwargs.get('options','')+' -c search_path='+self.schema
            return self.original(url,**kwargs)
        self.driver=patch.object(psycopg,'connect',side_effect=connect);self.driver.start()
        self.env=patch.dict(os.environ,{'DATABASE_URL':self.url,'VISITOR_HASH_KEY':''});self.env.start()
        self.before=datetime(2026,12,31,23,59,59,tzinfo=visits.LOCAL_TZ)
        self.after=datetime(2027,1,1,0,0,0,tzinfo=visits.LOCAL_TZ)
    def tearDown(self):
        self.env.stop();self.driver.stop()
        with self.original(self.url) as db:db.execute('DROP SCHEMA '+self.schema+' CASCADE')
    def test_concurrency_daily_total_and_persistent_cookie(self):
        identity,cookie=visits.browser_identity('')
        with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda _:visits.stats(identity,self.before),range(24)))
        self.assertEqual(visits.stats(now=self.before)['total'],1)
        with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda i:visits.stats('other-'+str(i),self.before),range(12)))
        self.assertEqual(visits.stats(now=self.before)['total'],13)
        self.assertEqual(visits.browser_identity(cookie.split(';')[0]),(identity,None))
        result=visits.stats(now=self.after);self.assertEqual((result['today'],result['total']),(0,13))
        self.assertEqual(visits.stats(identity,self.after)['total'],14)
        self.assertEqual(visits.stats(identity,self.after)['today'],1)
        self.assertEqual(visits.stats()['storage'],'postgresql')
    def test_migration_idempotence_and_rejection_of_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            path=folder+'/old.db'
            with patch.dict(os.environ,{'DATABASE_URL':'','STATS_DB_PATH':path}):
                visits.stats('old',self.before)
                old_key=visits.hash_key()
            result=pg.migrate(path,folder+'/old.visitors.key');self.assertEqual(result['total'],1)
            self.assertFalse(pg.migrate(path,folder+'/old.visitors.key')['imported'])
            self.assertEqual(pg.hash_key(),old_key)
            self.assertEqual(visits.stats('old',self.before)['total'],1)
            with patch.dict(os.environ,{'DATABASE_URL':'','STATS_DB_PATH':path}):visits.stats('another',self.before)
            with self.assertRaises(pg.CounterStorageError):pg.migrate(path,folder+'/old.visitors.key')
            self.assertEqual(visits.stats(now=self.before)['total'],1)
    def test_key_conflict_is_rejected(self):
        import base64
        pg.hash_key()
        with patch.dict(os.environ,{'VISITOR_HASH_KEY':base64.b64encode(b'x'*32).decode()}):
            with self.assertRaises(pg.CounterStorageError):pg.hash_key()
