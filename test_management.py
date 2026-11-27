import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.request import urlopen
import test_admin


class ManagementTests(unittest.TestCase):
    def test_admin_backup_and_settings(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'FREITSHOP_DATA_DIR':directory,'DATABASE_URL':'',
            'ADMIN_PASSWORD_HASH':hashlib.pbkdf2_hmac('sha256',b'test-only',bytes(16),600000).hex(),
            'ADMIN_PASSWORD_SALT':bytes(16).hex(),'ADMIN_USERNAME':'local-admin'
        }):
            # Reuse the HTTP client and exercise each operation through the normal routes.
            fixture=test_admin.AdminTests()
            fixture.setUp()
            try:
                call=fixture.call
                self.assertEqual(call('/api/admin/backup',{})[0],401)
                csrf=call('/api/admin/login',{'username':'local-admin','password':'test-only'})[1]['csrf']
                cfg=call('/api/admin/settings')[1]
                cfg.update(title='Minha loja',client='ca-pub-1234567890123456')
                self.assertEqual(call('/api/admin/settings',cfg)[0],403)
                self.assertEqual(call('/api/admin/settings',cfg,csrf)[0],200)
                with urlopen(fixture.base+'/') as page:
                    self.assertIn('Minha loja',page.read().decode())
                self.assertEqual(call('/api/feedback',{'rating':4,'comment':'Avaliação'})[0],200)
                status,backup=call('/api/admin/backup',{},csrf)
                self.assertEqual(status,200)
                self.assertEqual(backup['settings']['title'],'Minha loja')
                self.assertEqual(backup['comments'][0]['comment'],'Avaliação')
                self.assertEqual(call('/api/admin/comments/delete',{'id':backup['comments'][0]['id']},csrf)[0],200)
                self.assertEqual(call('/api/feedback')[1]['items'],[])
            finally:
                fixture.tearDown()
