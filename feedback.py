"""Feedback público sem cadastro, com criptografia autenticada em repouso."""
import base64
import json
import os
import re
import secrets
import sqlite3
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent

KEY_LOCK=threading.Lock()

class FeedbackError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def decode_key(value):
    try:
        key = base64.b64decode(value, validate=True)
        if len(key) != 32: raise ValueError()
        return key
    except (ValueError, TypeError):
        raise FeedbackError(503, 'Feedback indisponível: configuração de segurança incompleta.') from None


def security_config():
    if not os.environ.get('FEEDBACK_KEYS_JSON') and not os.environ.get('FEEDBACK_ACTIVE_KEY'):
        path=Path(os.environ.get('FEEDBACK_KEY_FILE') or str(Path(os.environ.get('FEEDBACK_DB_PATH') or ROOT/'data'/'feedback.sqlite3').with_suffix('.key')))
        with KEY_LOCK:
            path.parent.mkdir(parents=True,exist_ok=True)
            # Nunca substituir uma chave perdida de um banco já existente.
            dbpath=Path(os.environ.get('FEEDBACK_DB_PATH') or ROOT/'data'/'feedback.sqlite3')
            if not path.exists() and dbpath.exists() and dbpath.stat().st_size:
                raise FeedbackError(503,'Restaure a chave de criptografia usada pelo banco de avaliações existente.')
            try: fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            except FileExistsError: pass
            else:
                with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
            key=path.read_bytes()
            if len(key)!=32:raise FeedbackError(503,'Chave de avaliações inválida.')
        return {'auto_v1':key},'auto_v1',None
    try:
        raw = json.loads(os.environ.get('FEEDBACK_KEYS_JSON', '{}'))
        active = os.environ.get('FEEDBACK_ACTIVE_KEY', '')
        if not isinstance(raw, dict) or not raw or active not in raw: raise ValueError()
        keys = {k:decode_key(v) for k,v in raw.items() if re.fullmatch(r'[a-zA-Z0-9_-]{1,32}', k)}
        if len(keys)!=len(raw): raise ValueError()
        return keys, active, None
    except (ValueError, TypeError):
        raise FeedbackError(503, 'Feedback indisponível: configuração de segurança incompleta.') from None


def site_origin():
    value = os.environ.get('PUBLIC_SITE_URL', '').rstrip('/')
    if not value:return ''
    try:
        url = urlsplit(value)
        local = url.hostname in ('localhost','127.0.0.1')
        if not url.netloc or url.username or url.password or url.query or url.fragment or url.path: raise ValueError()
        if url.scheme!='https' and not (local and url.scheme=='http'): raise ValueError()
        return value
    except ValueError:
        raise FeedbackError(503, 'Configure a URL HTTPS do site para ativar o feedback.') from None


def ready():
    if os.environ.get('FEEDBACK_ENABLED','true').lower()!='true':
        raise FeedbackError(503, 'Avaliações em preparação. O administrador precisa ativar o formulário.')
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise FeedbackError(503,'Instale as dependências do servidor: pip install -r requirements.txt') from None
    security_config(); site_origin()


def public_config():
    try:
        ready()
        return {'enabled':True,'siteOrigin':site_origin()}
    except FeedbackError as e:
        return {'enabled':False,'message':str(e)}


def connect():
    path=Path(os.environ.get('FEEDBACK_DB_PATH') or str(ROOT/'data'/'feedback.sqlite3'))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    db.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT UNIQUE NOT NULL,
        key_id TEXT NOT NULL, nonce BLOB NOT NULL, ciphertext BLOB NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    db.execute('CREATE TABLE IF NOT EXISTS feedback_limits(owner TEXT PRIMARY KEY, window INTEGER NOT NULL, count INTEGER NOT NULL)')
    return db


def validate(data):
    if not isinstance(data,dict): raise FeedbackError(400,'Dados inválidos.')
    rating=data.get('rating'); comment=data.get('comment')
    if type(rating) is not int or not 1<=rating<=5:
        raise FeedbackError(400,'Escolha uma avaliação inteira de 1 a 5 estrelas.')
    if not isinstance(comment,str) or not comment.strip() or len(comment)>500:
        raise FeedbackError(400,'Escreva um comentário de 1 a 500 caracteres.')
    # Unicode code points; rejeita controles e surrogates não válidos.
    if any((ord(c)<32 and c not in '\n\t') or 0xD800<=ord(c)<=0xDFFF for c in comment):
        raise FeedbackError(400,'O comentário contém caracteres inválidos.')
    return {'rating':rating,'comment':comment.strip()}


def encrypt(owner,data):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    keys,active,_=security_config();nonce=secrets.token_bytes(12)
    ciphertext=AESGCM(keys[active]).encrypt(nonce,json.dumps(data,ensure_ascii=False).encode(),('freitshop-feedback:'+owner).encode())
    return active,nonce,ciphertext


def decode_row(row):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    identity,owner,key_id,nonce,ciphertext,created,updated=row
    try:
        keys,_,_=security_config()
        data=json.loads(AESGCM(keys[key_id]).decrypt(nonce,ciphertext,('freitshop-feedback:'+owner).encode()))
        data=validate(data)
    except Exception:
        raise FeedbackError(503,'Um registro não pôde ser lido com segurança. Contate o administrador.') from None
    return {'id':identity,'rating':data['rating'],'comment':data['comment'],'author':'Visitante','createdAt':created,'updatedAt':updated}


def rate_limit(db,owner):
    window=int(time.time()//60)
    db.execute('DELETE FROM feedback_limits WHERE window < ?', (window-1,))
    row=db.execute('SELECT window,count FROM feedback_limits WHERE owner=?',(owner,)).fetchone()
    count=row[1] if row and row[0]==window else 0
    if count>=6: raise FeedbackError(429,'Muitas alterações. Aguarde um minuto e tente novamente.')
    db.execute('INSERT OR REPLACE INTO feedback_limits(owner,window,count) VALUES(?,?,?)',(owner,window,count+1))


def submit_anonymous(data,rate_id):
    data=validate(data)
    # Um identificador aleatório por envio, sem vínculo com contas antigas ou IPs.
    owner='anonymous:'+secrets.token_hex(32)
    active,nonce,ciphertext=encrypt(owner,data)
    now=datetime.now(timezone.utc).isoformat()
    db=connect()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE');rate_limit(db,rate_id)
            db.execute('INSERT INTO feedback(owner,key_id,nonce,ciphertext,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                       (owner,active,nonce,ciphertext,now,now))
        return {'ok':True,'message':'Obrigado! Sua avaliação foi publicada.'}
    finally:db.close()


def listing(before=None):
    ready();db=connect()
    try:
        if before is None: rows=db.execute('SELECT * FROM feedback ORDER BY id DESC LIMIT 21').fetchall()
        else: rows=db.execute('SELECT * FROM feedback WHERE id < ? ORDER BY id DESC LIMIT 21',(before,)).fetchall()
        return {'items':[decode_row(row) for row in rows[:20]],'nextBefore':rows[19][0] if len(rows)>20 else None}
    finally:db.close()


def check_origin(origin,host=''):
    configured=site_origin()
    parsed=urlsplit(origin)
    allowed=(origin==configured) if configured else bool(host and parsed.scheme in ('http','https') and parsed.netloc==host and not parsed.path and not parsed.username and not parsed.query and not parsed.fragment)
    if not allowed: raise FeedbackError(403,'Origem da solicitação não permitida.')
