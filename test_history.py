import os, tempfile, unittest, threading, json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from urllib.error import HTTPError
import price_history as history
import server

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'PRICE_HISTORY_DB_PATH':str(Path(self.tmp.name)/'history.sqlite3')})
        self.env.start()
        self.offer=dict(name='Modelo 256GB',store='Loja A',url='https://example.com/a',condition='',price=1000)
        self.key=history.offer_key(self.offer)
    def tearDown(self): self.env.stop();self.tmp.cleanup()
    def test_store_variant_identity(self):
        for change in [{'store':'Loja B'},{'name':'Modelo 128GB'},{'condition':'used'},{'url':'https://example.com/b'}]:
            self.assertNotEqual(self.key,history.offer_key({**self.offer,**change}))
        self.assertEqual(self.key,history.offer_key({**self.offer,'price':800}))
    def test_daily_last_observation_and_no_backfill(self):
        history.record([self.offer],'2026-10-24T12:00:00+00:00')
        history.record([{**self.offer,'price':900}],'2026-10-24T15:00:00+00:00')
        history.record([{**self.offer,'price':1100}],'2026-10-24T10:00:00+00:00')
        data=history.get_history(self.key,4,datetime(2026,10,25,tzinfo=timezone.utc))
        self.assertEqual(len(data['points']),1)
        self.assertEqual(data['points'][0]['price'],900)
        self.assertEqual(data['firstRecorded'],'2026-10-24')
    def test_month_end_and_period(self):
        history.record([self.offer],'2026-01-20T12:00:00+00:00')
        history.record([self.offer],'2026-02-28T12:00:00+00:00')
        now=datetime(2026,3,31,12,tzinfo=timezone.utc)
        data=history.get_history(self.key,1,now)
        self.assertEqual(data['start'],'2026-02-28')
        self.assertEqual(len(data['points']),1)
        self.assertEqual(len(history.get_history(self.key,3,now)['points']),2)
    def test_retention_boundary_and_orphan_cleanup(self):
        history.record([self.offer],'2026-06-24T12:00:00+00:00')
        history.record([self.offer],'2026-06-25T12:00:00+00:00')
        other={**self.offer,'store':'Outra loja'}
        history.record([other],'2026-06-24T12:00:00+00:00')
        now=datetime(2026,10,25,12,tzinfo=timezone.utc)
        self.assertEqual(history.cleanup(now),2)
        db=history.connection()
        try:
            self.assertEqual(db.execute('SELECT day FROM price_observations').fetchall(),[('2026-06-25',)])
            self.assertEqual(db.execute('SELECT count(*) FROM price_offers').fetchone()[0],1)
        finally:db.close()
        self.assertEqual(history.cleanup(now),0)
        self.assertIsNone(history.get_history(self.key,4,datetime(2026,10,26,12,tzinfo=timezone.utc)))
    def test_read_also_deletes_expired(self):
        history.record([self.offer],'2026-01-01T12:00:00+00:00')
        self.assertIsNone(history.get_history(self.key,4,datetime(2026,10,25,12,tzinfo=timezone.utc)))
        self.assertEqual(history.months_before(datetime(2026,6,30).date(),4).isoformat(),'2026-02-28')
    def test_routes(self):
        srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
        base='http://127.0.0.1:'+str(srv.server_port)
        try:
            for suffix in ['offer=bad&months=4','offer='+self.key+'&months=999','offer='+self.key+'&months=6']:
                with self.assertRaises(HTTPError) as e:urlopen(base+'/api/price-history?'+suffix)
                self.assertEqual(e.exception.code,400)
            with self.assertRaises(HTTPError) as e:urlopen(base+'/api/price-history?offer='+self.key)
            self.assertEqual(e.exception.code,404)
            history.record([self.offer],datetime.now(timezone.utc).isoformat())
            with urlopen(base+'/api/price-history?offer='+self.key) as r:self.assertEqual(len(json.load(r)['points']),1)
        finally:srv.shutdown();srv.server_close();t.join()
