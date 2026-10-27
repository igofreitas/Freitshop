"""Uma visita por navegador/dia (UTC−3), com HMAC e sem guardar o IP bruto."""
import base64
import hashlib
import hmac
import ipaddress
import os
import secrets
import re
from http.cookies import SimpleCookie, CookieError
import sqlite3
import threading
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LOCAL_TZ=timezone(timedelta(hours=-3))
KEY_LOCK=threading.Lock()

def db_path():
    directory=Path(os.environ.get('FREITSHOP_DATA_DIR',str(ROOT/'data')))
    return Path(os.environ.get('STATS_DB_PATH',str(directory/'access.sqlite3')))

def canonical_ip(value):
    address=ipaddress.ip_address(value.strip())
    if isinstance(address,ipaddress.IPv6Address) and address.ipv4_mapped:address=address.ipv4_mapped
    return address.compressed

def client_ip(peer,headers):
    peer=canonical_ip(peer)
    hops=int(os.environ.get('TRUSTED_PROXY_HOPS','0'))
    if not 0<=hops<=10:raise ValueError('Número de proxies inválido.')
    if not hops:return peer  # Não confiar em XFF enviado diretamente por visitantes.
    raw=headers.get('X-Forwarded-For','')
    if len(raw)>4096:raise ValueError('Cadeia de proxies inválida.')
    chain=[canonical_ip(part) for part in raw.split(',') if part.strip()]+[peer]
    if len(chain)<=hops:raise ValueError('Cadeia de proxies incompleta.')
    return chain[-hops-1]

def hash_key():
    raw=os.environ.get('VISITOR_HASH_KEY','')
    if raw:
        key=base64.b64decode(raw,validate=True)
        if len(key)!=32:raise ValueError('VISITOR_HASH_KEY precisa ter 32 bytes.')
        return key
    path=Path(os.environ.get('VISITOR_KEY_FILE',str(db_path().with_suffix('.visitors.key'))))
    with KEY_LOCK:
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:pass
        else:
            with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
        key=path.read_bytes()
        if len(key)!=32:raise ValueError('Chave do contador inválida.')
        return key

def day_of(now=None):return (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ).date().isoformat()

def daily_token(ip,day=None,purpose='visits'):
    message=f'{purpose}|{day or day_of()}|{canonical_ip(ip)}'.encode()
    return hmac.new(hash_key(),message,hashlib.sha256).hexdigest()

def browser_identity(cookie_header):
    jar=SimpleCookie()
    try: jar.load(cookie_header or '')
    except CookieError: pass
    value=jar.get('freitshop_visitor')
    value=value.value if value else ''
    identity,_,signature=value.partition('.')
    key=hash_key()
    def sign(identity):return hmac.new(key,('cookie|'+identity).encode(),hashlib.sha256).hexdigest()
    if re.fullmatch(r'[a-f0-9]{64}',identity) and hmac.compare_digest(signature,sign(identity)):
        return identity,None
    identity=secrets.token_hex(32)
    cookie='freitshop_visitor='+identity+'.'+sign(identity)+'; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax'
    if os.environ.get('PUBLIC_SITE_URL','').startswith('https://'):cookie+='; Secure'
    return identity,cookie

def stats(visitor_id=None,now=None):
    instant=now or datetime.now(LOCAL_TZ)
    today=day_of(instant);path=db_path();path.parent.mkdir(parents=True,exist_ok=True)
    token=hmac.new(hash_key(),f'browser|{today}|{visitor_id}'.encode(),hashlib.sha256).hexdigest() if visitor_id is not None else None
    db=sqlite3.connect(path,timeout=10)
    try:
        with db:
            # Novas tabelas: a contagem antiga de visualizações não era deduplicada.
            db.execute('CREATE TABLE IF NOT EXISTS unique_visit_totals(day TEXT PRIMARY KEY,count INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS daily_visitors(day TEXT NOT NULL,token TEXT NOT NULL,PRIMARY KEY(day,token))')
            db.execute('DELETE FROM daily_visitors WHERE day < ?',(today,))
            if token is not None:
                inserted=db.execute('INSERT OR IGNORE INTO daily_visitors(day,token) VALUES(?,?)',(today,token)).rowcount
                if inserted:
                    db.execute('INSERT INTO unique_visit_totals(day,count) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET count=count+1',(today,))
            total=db.execute('SELECT COALESCE(SUM(count),0) FROM unique_visit_totals').fetchone()[0]
            row=db.execute('SELECT count FROM unique_visit_totals WHERE day=?',(today,)).fetchone()
        return {'total':total,'today':row[0] if row else 0,'date':today,'timezone':'UTC-03:00','metric':'unique_browser_per_day','serverTime':int(instant.timestamp()*1000)}
    finally:db.close()
