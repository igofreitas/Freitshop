import io, json, os, unittest, tempfile
from unittest.mock import patch
from urllib.error import HTTPError
import server

class Tests(unittest.TestCase):
    def setUp(self):
        server.CACHE.clear()
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'PRICE_HISTORY_DB_PATH':self.tmp.name+'/history.sqlite3'})
        self.env.start()
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def fixture(self, **overrides):
        return dict(title='Modelo 256GB',source='Loja A',price='R$ 1.250,00',extracted_price=1250,product_link='https://example.com/item',**overrides)
    def test_normalization(self):
        p=self.fixture(); bad={**p,'price':'$ 1250'}; unsafe={**p,'product_link':'javascript:alert(1)'}
        rows=server.normalize({'shopping_results':[p,p,bad,unsafe,{**p,'extracted_price':float('nan')},{**p,'extracted_price':True}]})
        self.assertEqual(len(rows),1); self.assertEqual(rows[0]['price'],1250); self.assertIsNone(rows[0]['rating'])
    def test_missing_key(self):
        with patch.dict(os.environ,{'SERPAPI_KEY':''}): self.assertEqual(server.search('Samsung')[0],503)
    def test_search_cache_and_locale(self):
        payload=json.dumps({'shopping_results':[self.fixture()]}).encode()
        with patch.dict(os.environ,{'SERPAPI_KEY':'test'}), patch('server.urlopen',return_value=io.BytesIO(payload)) as req:
            status,data=server.search('Samsung'); self.assertEqual(status,200); self.assertFalse(data['cached']); self.assertTrue(data['historySaved']); self.assertEqual(len(data['offers'][0]['historyId']),64)
            self.assertTrue(server.search('samsung')[1]['cached']); self.assertEqual(req.call_count,1)
            self.assertIn('gl=br',req.call_args.args[0].full_url)
    def test_provider_failure(self):
        with patch.dict(os.environ,{'SERPAPI_KEY':'test'}), patch('server.urlopen',side_effect=HTTPError('test',429,'quota',{},None)):
            self.assertEqual(server.search('Samsung')[0],502)
    def test_empty_results(self):
        with patch.dict(os.environ,{'SERPAPI_KEY':'test'}), patch('server.urlopen',return_value=io.BytesIO(b'{}')):
            self.assertEqual(server.search('Samsung')[1]['offers'],[])

if __name__=='__main__': unittest.main()
