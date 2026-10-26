import os, tempfile, unittest, threading, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.request import urlopen, build_opener, HTTPCookieProcessor, Request
from http.cookiejar import CookieJar
from urllib.error import HTTPError
import server

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'STATS_DB_PATH':str(Path(self.tmp.name)/'counts.db'), 'ADSENSE_CLIENT':'', 'ADSENSE_SLOT':'', 'ADSENSE_ENABLED':'false','PRIVACY_URL':'','TRUSTED_PROXY_HOPS':'0','VISITOR_HASH_KEY':''})
        self.env.start()
    def tearDown(self): self.env.stop(); self.tmp.cleanup()
    def test_concurrency_persistence(self):
        self.assertEqual(server.stats()['total'],0)
        with ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(lambda _:server.stats(True,visitor_id='browser-one'), range(40)))
        self.assertEqual(server.stats()['total'],1)
        self.assertEqual(server.stats()['today'],1)
        self.assertEqual(server.stats()['total'],1) # leitura não incrementa
    def test_ad_gate(self):
        self.assertFalse(server.ad_config()['enabled'])
        with patch.dict(os.environ,{'ADSENSE_CLIENT':'ca-pub-1234567890123456','ADSENSE_SLOT':'1234567890','ADSENSE_ENABLED':'true'}):
            self.assertFalse(server.ad_config()['enabled'])
            with patch.dict(os.environ,{'PRIVACY_URL':'https://example.com/privacy'}):self.assertTrue(server.ad_config()['enabled'])
        with patch.dict(os.environ,{'ADSENSE_CLIENT':'<script>bad</script>'}):self.assertEqual(server.ad_config()['client'],'')
    def test_routes(self):
        srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
        base='http://127.0.0.1:'+str(srv.server_port)
        try:
            browser=build_opener(HTTPCookieProcessor(CookieJar()))
            for _ in range(3):
                with browser.open(Request(base+'/api/visit',data=b'')) as r:self.assertEqual(json.load(r)['total'],1)
            other=build_opener(HTTPCookieProcessor(CookieJar()))
            with other.open(Request(base+'/api/visit',data=b'')) as r:self.assertEqual(json.load(r)['total'],2)
            for path in ['/', '/index.html']:
                with urlopen(base+path) as r:
                    content=r.read();self.assertIn(b'accessCounter',content);self.assertIn('2 no total • 2 hoje'.encode(),content)
            with urlopen(base+'/healthz') as r:self.assertEqual(r.status,200)
            with urlopen(base+'/api/stats') as r:self.assertEqual(json.load(r)['total'],2)
            with self.assertRaises(HTTPError):urlopen(base+'/data/access.sqlite3')
            with self.assertRaises(HTTPError):urlopen(base+'/ads.txt')
            with patch.dict(os.environ,{'ADSENSE_CLIENT':'ca-pub-1234567890123456'}):
                with urlopen(base+'/ads.txt') as r:self.assertIn(b'google.com, pub-1234567890123456, DIRECT',r.read())
                with urlopen(base+'/') as r:self.assertIn(b'google-adsense-account',r.read())
        finally:srv.shutdown();srv.server_close();t.join()
    def test_database_failure_does_not_hide_home(self):
        # configuração de caminho inválida é reportada pelo contador, não pela busca.
        with patch.dict(os.environ,{'STATS_DB_PATH':self.tmp.name}):
            with self.assertRaises(Exception):server.stats()

if __name__=='__main__':unittest.main()

class CounterRestartTests(unittest.TestCase):
    def test_same_totals_after_restart_and_read_only_polling(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'STATS_DB_PATH':directory+'/stats.db','VISITOR_HASH_KEY':''}):
            def start():
                srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
                thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start()
                return srv,thread,'http://127.0.0.1:'+str(srv.server_port)
            pc=build_opener(HTTPCookieProcessor(CookieJar()))
            phone=build_opener(HTTPCookieProcessor(CookieJar()))
            srv,thread,base=start()
            try:
                for client in (pc,phone):
                    with client.open(Request(base+'/api/visit',data=b'')) as r:r.read()
                for client in (pc,phone):
                    with client.open(base+'/api/stats') as r:self.assertEqual(json.load(r)['total'],2)
            finally:srv.shutdown();srv.server_close();thread.join()
            srv,thread,base=start()
            try:
                for client in (pc,phone):
                    with client.open(Request(base+'/api/visit',data=b'')) as r:self.assertEqual(json.load(r)['total'],2)
                for _ in range(5):
                    with pc.open(base+'/api/stats') as r:self.assertEqual(json.load(r)['total'],2)
            finally:srv.shutdown();srv.server_close();thread.join()
