"""Contador PostgreSQL persistente. Nunca faz fallback silencioso para SQLite."""
import os,secrets,base64,hashlib,hmac,sqlite3
from contextlib import contextmanager
from pathlib import Path

class CounterStorageError(Exception):pass

@contextmanager
def connection():
    try:
        import psycopg
        url=os.environ.get('DATABASE_URL','').strip()
        if not url:raise CounterStorageError('Configure DATABASE_URL no Render.')
        # A URL é usada somente no servidor e nunca incluída nas mensagens públicas.
        with psycopg.connect(url,connect_timeout=5,options='-c statement_timeout=10000 -c lock_timeout=10000') as db:
            # Serializa inicialização, migração e gravações entre instâncias.
            db.execute('SELECT pg_advisory_xact_lock(726184902)')
            db.execute('CREATE TABLE IF NOT EXISTS freitshop_counter_settings(name TEXT PRIMARY KEY,value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS freitshop_visit_totals(day DATE PRIMARY KEY,count BIGINT NOT NULL CHECK(count>=0))')
            db.execute('CREATE TABLE IF NOT EXISTS freitshop_daily_visitors(day DATE NOT NULL,token TEXT NOT NULL,PRIMARY KEY(day,token))')
            yield db
    except CounterStorageError:raise
    except Exception as exc:
        # Não propagar DSN, senha, hostname ou mensagens do driver à resposta HTTP.
        raise CounterStorageError('Contador indisponível. Verifique DATABASE_URL e o acesso ao PostgreSQL.') from None

def key_in(db):
    raw=os.environ.get('VISITOR_HASH_KEY','').strip()
    try:
        override=base64.b64decode(raw,validate=True) if raw else None
        if override is not None and len(override)!=32:raise ValueError()
    except ValueError:raise CounterStorageError('VISITOR_HASH_KEY inválida.') from None
    row=db.execute("SELECT value FROM freitshop_counter_settings WHERE name='visitor_key'").fetchone()
    if row:
        key=base64.b64decode(row[0],validate=True)
        if len(key)!=32:raise CounterStorageError('Chave persistida inválida.')
        if override is not None and not hmac.compare_digest(key,override):
            raise CounterStorageError('VISITOR_HASH_KEY difere da chave persistida. Preserve a chave original.')
        return key
    key=override or secrets.token_bytes(32)
    db.execute("INSERT INTO freitshop_counter_settings(name,value) VALUES('visitor_key',%s)",(base64.b64encode(key).decode(),))
    return key

def hash_key():
    with connection() as db:return key_in(db)

def stats(visitor_id,instant,today):
    with connection() as db:
        key=key_in(db)
        if visitor_id is not None:
            token=hmac.new(key,f'browser|{today}|{visitor_id}'.encode(),hashlib.sha256).hexdigest()
            inserted=db.execute('INSERT INTO freitshop_daily_visitors(day,token) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING token',(today,token)).fetchone()
            if inserted:
                db.execute('INSERT INTO freitshop_visit_totals(day,count) VALUES(%s,1) ON CONFLICT(day) DO UPDATE SET count=freitshop_visit_totals.count+1',(today,))
            db.execute('DELETE FROM freitshop_daily_visitors WHERE day < %s',(today,))
        row=db.execute('SELECT COALESCE(SUM(count),0),COALESCE(SUM(CASE WHEN day=%s THEN count ELSE 0 END),0) FROM freitshop_visit_totals',(today,)).fetchone()
        return {'total':int(row[0]),'today':int(row[1]),'date':today,'timezone':'UTC-03:00','metric':'unique_browser_per_day','serverTime':int(instant.timestamp()*1000),'storage':'postgresql'}

def migrate(source,key_file):
    # Migração explícita: somente para destino vazio, nunca mesclar totais ambíguos.
    source=Path(source).resolve();key_file=Path(key_file)
    if not source.is_file() or not key_file.is_file():raise CounterStorageError('Informe o banco SQLite e sua chave original existentes.')
    key=key_file.read_bytes()
    if len(key)!=32:raise CounterStorageError('Chave SQLite inválida.')
    old=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
    try:
        old.execute('BEGIN')
        totals=old.execute('SELECT day,count FROM unique_visit_totals ORDER BY day').fetchall()
        visitors=old.execute('SELECT day,token FROM daily_visitors ORDER BY day,token').fetchall()
    finally:old.close()
    from datetime import date
    for day,count in totals:
        date.fromisoformat(day)
        if type(count) is not int or count<0:raise CounterStorageError('Contagem de origem inválida.')
    fingerprint=hashlib.sha256(repr((totals,visitors)).encode()+key).hexdigest()
    with connection() as db:
        previous=db.execute("SELECT value FROM freitshop_counter_settings WHERE name='sqlite_import'").fetchone()
        if previous:
            if previous[0]==fingerprint:return {'imported':False,'message':'Este backup já foi importado; nenhum valor foi somado novamente.'}
            raise CounterStorageError('Outro backup já foi importado. Migração cancelada.')
        if db.execute('SELECT EXISTS(SELECT 1 FROM freitshop_visit_totals) OR EXISTS(SELECT 1 FROM freitshop_daily_visitors)').fetchone()[0]:
            raise CounterStorageError('PostgreSQL já contém visitas. Migração cancelada sem alterar dados.')
        raw=os.environ.get('VISITOR_HASH_KEY','').strip()
        if raw and not hmac.compare_digest(base64.b64decode(raw,validate=True),key):raise CounterStorageError('VISITOR_HASH_KEY precisa ser igual à chave SQLite original.')
        for day,count in totals:db.execute('INSERT INTO freitshop_visit_totals(day,count) VALUES(%s,%s)',(day,count))
        for day,token in visitors:db.execute('INSERT INTO freitshop_daily_visitors(day,token) VALUES(%s,%s)',(day,token))
        db.execute("INSERT INTO freitshop_counter_settings(name,value) VALUES('visitor_key',%s) ON CONFLICT(name) DO UPDATE SET value=EXCLUDED.value",(base64.b64encode(key).decode(),))
        db.execute("INSERT INTO freitshop_counter_settings(name,value) VALUES('sqlite_import',%s)",(fingerprint,))
    return {'imported':True,'days':len(totals),'total':sum(row[1] for row in totals)}
