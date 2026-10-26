import os,tempfile,unittest,threading,json
from unittest.mock import patch
from urllib.request import Request,build_opener,HTTPCookieProcessor
from urllib.error import HTTPError
from http.cookiejar import CookieJar
import server,admin

class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'ADMIN_DB_PATH':self.tmp.name+'/admin.db','STATS_DB_PATH':self.tmp.name+'/stats.db','PUBLIC_SITE_URL':'','TRUSTED_PROXY_HOPS':'0'})
        self.env.start()
        self.srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.srv.server_port)
        self.client=build_opener(HTTPCookieProcessor(CookieJar()))
    def tearDown(self):
        self.srv.shutdown();self.srv.server_close();self.thread.join();self.env.stop();self.tmp.cleanup()
    def call(self,path,data=None,csrf='',origin=None):
        req=Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Origin':origin or self.base,'X-CSRF-Token':csrf})
        try:
            with self.client.open(req) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    @unittest.skipUnless(os.environ.get("TEST_ADMIN_PASSWORD"),"Defina TEST_ADMIN_PASSWORD para testar o login real.")
    def test_crud_and_authorization(self):
        self.assertEqual(self.call('/api/admin/sponsors',{'name':'Loja','url':'https://example.com'})[0],401)
        self.assertEqual(self.call('/api/admin/login',{'username':'x','password':'bad'})[0],401)
        # O teste usa a senha do ambiente; não distribui credencial em texto no ZIP.
        status,result=self.call('/api/admin/login',{'username':'igfreitasAdmin','password':os.environ['TEST_ADMIN_PASSWORD']})
        self.assertEqual(status,200);csrf=result['csrf']
        self.assertTrue(self.call('/api/admin/session')[1]['authenticated'])
        self.assertEqual(self.call('/api/admin/sponsors',{'name':'Loja','url':'https://example.com'})[0],403)
        self.assertEqual(self.call('/api/admin/sponsors',{'name':'Loja','url':'https://example.com'},csrf,'https://evil.com')[0],403)
        self.assertEqual(self.call('/api/admin/sponsors',{'name':'Loja','url':'javascript:alert(1)'},csrf)[0],400)
        self.assertEqual(self.call('/api/admin/sponsors',{'name':'Loja','url':'https://example.com'},csrf)[0],200)
        items=self.call('/api/sponsors')[1]['items'];self.assertEqual(len(items),1);identity=items[0]['id']
        self.assertEqual(self.call('/api/admin/sponsors',{'id':identity,'name':'Nova loja','url':'https://example.org'},csrf)[0],200)
        self.assertEqual(admin.listing()['items'][0]['name'],'Nova loja')
        self.assertEqual(self.call('/api/admin/sponsors/delete',{'id':identity},csrf)[0],200)
        self.assertEqual(admin.listing()['items'],[])
        self.assertEqual(self.call('/api/admin/logout',{},csrf)[0],200)
        self.assertFalse(self.call('/api/admin/session')[1]['authenticated'])
        self.assertEqual(self.call('/api/admin/sponsors',{'name':'Loja','url':'https://example.com'},csrf)[0],401)
    def test_rate_limit(self):
        for _ in range(10):self.assertEqual(self.call('/api/admin/login',{'username':'x','password':'bad'})[0],401)
        self.assertEqual(self.call('/api/admin/login',{'username':'x','password':'bad'})[0],429)
    def test_public_files_do_not_expose_backend(self):
        for path in ['/admin.py','/data/admin.sqlite3']:
            self.assertEqual(self.call(path)[0],404)
        with self.client.open(self.base+'/') as r:
            page=r.read().decode();self.assertNotIn('storeFilter',page);self.assertNotIn('priceRange',page);self.assertIn('adminPanel',page)
