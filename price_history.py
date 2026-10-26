"""Histórico de preços observados, por oferta/loja. Não gera preços retroativos."""
import calendar
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCAL_TZ = timezone(timedelta(hours=-3))

def offer_key(offer):
    # Não mistura modelos, condições, vendedores ou links distintos por similaridade.
    identity = [offer['name'], offer['store'], offer['url'], offer.get('condition', '')]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()

def connection():
    path = Path(os.environ.get('PRICE_HISTORY_DB_PATH') or os.environ.get('STATS_DB_PATH') or str(ROOT/'data'/'access.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS price_offers (id TEXT PRIMARY KEY, name TEXT NOT NULL, store TEXT NOT NULL, url TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS price_observations (offer_id TEXT NOT NULL, day TEXT NOT NULL, price REAL NOT NULL, observed_at TEXT NOT NULL, PRIMARY KEY(offer_id,day))')
    return db

def record(offers, fetched_at):
    day = datetime.fromisoformat(fetched_at).astimezone(LOCAL_TZ).date().isoformat()
    db = connection()
    try:
        with db:
            for offer in offers:
                identity = offer_key(offer)
                db.execute('INSERT OR REPLACE INTO price_offers(id,name,store,url) VALUES(?,?,?,?)', (identity,offer['name'],offer['store'],offer['url']))
                # Última observação de cada dia. Respostas antigas não sobrescrevem novas.
                db.execute('''INSERT INTO price_observations(offer_id,day,price,observed_at) VALUES(?,?,?,?)
                              ON CONFLICT(offer_id,day) DO UPDATE SET price=excluded.price,observed_at=excluded.observed_at
                              WHERE excluded.observed_at >= price_observations.observed_at''',
                           (identity,day,offer['price'],fetched_at))
    finally: db.close()

def get_history(identity, months, now=None):
    today = (now or datetime.now(LOCAL_TZ)).astimezone(LOCAL_TZ).date()
    count = today.year*12 + today.month-1-months
    year, month0 = divmod(count,12)
    start = today.replace(year=year,month=month0+1,day=min(today.day,calendar.monthrange(year,month0+1)[1]))
    db = connection()
    try:
        row = db.execute('SELECT name,store,url FROM price_offers WHERE id=?',(identity,)).fetchone()
        if row is None: return None
        points = db.execute('SELECT day,price,observed_at FROM price_observations WHERE offer_id=? AND day>=? AND day<=? ORDER BY day', (identity,start.isoformat(),today.isoformat())).fetchall()
        first = db.execute('SELECT MIN(day) FROM price_observations WHERE offer_id=?',(identity,)).fetchone()[0]
        return dict(name=row[0],store=row[1],url=row[2],months=months,start=start.isoformat(),end=today.isoformat(),firstRecorded=first,
                    points=[dict(date=p[0],price=p[1],observedAt=p[2]) for p in points])
    finally: db.close()
