import base64,json,os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import feedback,server

class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.key=base64.b64encode(os.urandom(32)).decode()
        self.env=patch.dict(os.environ,{'FEEDBACK_ENABLED':'true','FEEDBACK_KEYS_JSON':json.dumps({'v1':self.key}),'FEEDBACK_ACTIVE_KEY':'v1','FEEDBACK_DB_PATH':self.tmp.name+'/feedback.db','STATS_DB_PATH':self.tmp.name+'/stats.db','PUBLIC_SITE_URL':'https://example.com','TRUSTED_PROXY_HOPS':'0','VISITOR_HASH_KEY':''})
        self.env.start()
    def tearDown(self):self.env.stop();self.tmp.cleanup()
    def test_validation(self):
        self.assertEqual(len(feedback.validate({'rating':5,'comment':'🙂'*500})['comment']),500)
        for data in [{'rating':6,'comment':'ok'},{'rating':0,'comment':'ok'},{'rating':True,'comment':'ok'},{'rating':1.5,'comment':'ok'},{'rating':5,'comment':'a'*501},{'rating':5,'comment':'   '},[]]:
            with self.assertRaises(feedback.FeedbackError):feedback.validate(data)
    def test_anonymous_encrypted(self):
        feedback.submit_anonymous({'rating':5,'comment':'Texto privado em disco'},'rate-hash')
        feedback.submit_anonymous({'rating':4,'comment':'Outro'},'rate-hash')
        self.assertNotIn(b'Texto privado',Path(os.environ['FEEDBACK_DB_PATH']).read_bytes())
        items=feedback.listing()['items'];self.assertEqual(len(items),2);self.assertTrue(all(p['author']=='Visitante' for p in items))
    def test_rate_limit(self):
        for _ in range(6):feedback.submit_anonymous({'rating':5,'comment':'oi'},'rate-hash')
        with self.assertRaises(feedback.FeedbackError) as e:feedback.submit_anonymous({'rating':5,'comment':'oi'},'rate-hash')
        self.assertEqual(e.exception.status,429)
    def test_tamper(self):
        feedback.submit_anonymous({'rating':5,'comment':'oi'},'rate-hash');db=feedback.connect()
        with db:db.execute('UPDATE feedback SET ciphertext=?',(b'tampered',))
        db.close()
        with self.assertRaises(feedback.FeedbackError):feedback.listing()
    def test_legacy_data_and_rotation(self):
        key,nonce,ciphertext=feedback.encrypt('legacy-hmac',{'rating':3,'comment':'Avaliação anterior'})
        db=feedback.connect()
        with db:db.execute('INSERT INTO feedback(owner,key_id,nonce,ciphertext,created_at,updated_at) VALUES(?,?,?,?,?,?)',('legacy-hmac',key,nonce,ciphertext,'2026-01-01','2026-01-01'))
        db.close()
        with patch.dict(os.environ,{'FEEDBACK_KEYS_JSON':json.dumps({'v1':self.key,'v2':base64.b64encode(os.urandom(32)).decode()}),'FEEDBACK_ACTIVE_KEY':'v2'}):
            self.assertEqual(feedback.listing()['items'][0]['comment'],'Avaliação anterior')
    def test_no_firebase_dependency(self):
        with patch.dict(os.environ,{'FIREBASE_WEB_CONFIG':'','FIREBASE_SERVICE_ACCOUNT_JSON':'','FEEDBACK_ID_KEY':''}):
            config=feedback.public_config();self.assertTrue(config['enabled']);self.assertNotIn('firebase',config);self.assertNotIn(self.key,json.dumps(config))
    def test_http_anonymous(self):
        srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);t=threading.Thread(target=srv.serve_forever,daemon=True);t.start()
        base='http://127.0.0.1:'+str(srv.server_port)
        def call(path,data=None,origin='https://example.com'):
            req=Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Origin':origin})
            try:
                with urlopen(req) as r:return r.status,json.load(r)
            except HTTPError as e:return e.code,json.load(e)
        try:
            self.assertEqual(call('/api/feedback',{'rating':5,'comment':'Sem login'})[0],200)
            self.assertEqual(call('/api/feedback')[1]['items'][0]['comment'],'Sem login')
            self.assertEqual(call('/api/feedback',{'rating':5,'comment':'bad'},'https://evil.com')[0],403)
            self.assertEqual(call('/api/feedback',{'rating':9,'comment':'bad'})[0],400)
            self.assertEqual(call('/api/feedback',{'rating':5,'comment':'a'*9000})[0],413)
            self.assertEqual(call('/api/feedback/delete',{})[0],404)
            self.assertEqual(call('/api/feedback/mine')[0],404)
        finally:srv.shutdown();srv.server_close();t.join()

    def test_auto_setup_and_publish_without_manual_configuration(self):
        with patch.dict(os.environ,{'FEEDBACK_KEYS_JSON':'','FEEDBACK_ACTIVE_KEY':'','PUBLIC_SITE_URL':''}):
            os.environ.pop('FEEDBACK_ENABLED',None)
            self.assertTrue(feedback.public_config()['enabled'])
            feedback.check_origin('http://localhost:8000','localhost:8000')
            with self.assertRaises(feedback.FeedbackError):feedback.check_origin('https://evil.com','localhost:8000')
            feedback.submit_anonymous({'rating':5,'comment':'Publicação automática'},'rate')
            self.assertEqual(feedback.listing()['items'][0]['comment'],'Publicação automática')
            self.assertTrue(Path(self.tmp.name+'/feedback.key').exists())
            Path(self.tmp.name+'/feedback.key').unlink()
            with self.assertRaises(feedback.FeedbackError):feedback.security_config()
