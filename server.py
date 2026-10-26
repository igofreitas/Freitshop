"""FreitShop: servidor local Python 3.10+, sem dependências externas."""
import json, os, time, math, threading, sqlite3, re
from datetime import timedelta
from datetime import datetime, timezone
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, parse_qs, urlencode
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
CACHE = {}
LOCK = threading.Lock()

def stats(increment=False):
    # Contagem agregada de requisições HTML, sem IP, cookies ou identidade.
    path = Path(os.environ.get('STATS_DB_PATH', str(ROOT / 'data' / 'access.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone(timedelta(hours=-3))).date().isoformat()
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('CREATE TABLE IF NOT EXISTS views (day TEXT PRIMARY KEY, count INTEGER NOT NULL)')
        if increment:
            db.execute('INSERT INTO views(day,count) VALUES(?,1) ON CONFLICT(day) DO UPDATE SET count=count+1', (today,))
        total = db.execute('SELECT COALESCE(SUM(count),0) FROM views').fetchone()[0]
        row = db.execute('SELECT count FROM views WHERE day=?', (today,)).fetchone()
    return {'total':total, 'today':row[0] if row else 0, 'date':today, 'timezone':'UTC-03:00'}

def ad_config():
    client = os.environ.get('ADSENSE_CLIENT', '').strip()
    slot = os.environ.get('ADSENSE_SLOT', '').strip()
    if not re.fullmatch(r'ca-pub-[0-9]{16}', client): client = ''
    if not re.fullmatch(r'[0-9]+', slot): slot = ''
    privacy = safe_url(os.environ.get('PRIVACY_URL', ''))
    enabled = bool(client and slot and privacy and os.environ.get('ADSENSE_ENABLED') == 'true')
    return {'client':client, 'slot':slot, 'enabled':enabled, 'privacyUrl':privacy}

def safe_url(value):
    if not isinstance(value, str): return ''
    try:
        u = urlsplit(value)
        return value if u.scheme in ('https', 'http') and u.netloc and not u.username else ''
    except ValueError: return ''

def normalize(data):
    result, seen = [], set()
    for item in data.get('shopping_results', []):
        price = item.get('extracted_price')
        # Não confundir preço de parcela ou moeda estrangeira com preço total em BRL.
        raw_price = str(item.get('price', ''))
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0: continue
        if 'R$' not in raw_price and 'BRL' not in raw_price: continue
        url = safe_url(item.get('product_link')) or safe_url(item.get('link'))
        name, store = item.get('title'), item.get('source')
        if not url or not isinstance(name, str) or not isinstance(store, str): continue
        key = (url, store, price)
        if key in seen: continue
        seen.add(key)
        rating = item.get('rating')
        if isinstance(rating, bool) or not isinstance(rating, (int, float)) or not 0 <= rating <= 5: rating = None
        result.append(dict(id=str(len(result)), name=name, store=store, price=price, url=url,
                           image=safe_url(item.get('thumbnail')), rating=rating,
                           delivery=str(item.get('delivery') or ''), condition=str(item.get('second_hand_condition') or '')))
    return result

def search(query):
    key = os.environ.get('SERPAPI_KEY', '').strip()
    if not key: return 503, {'error':'Configure SERPAPI_KEY no servidor para ativar a busca online. Veja o LEIA-ME.md.'}
    with LOCK:
        entry = CACHE.get(query.casefold())
        if entry and time.monotonic()-entry[0] < 300: return 200, {**entry[1], 'cached':True}
        params = urlencode(dict(engine='google_shopping', q=query, gl='br', hl='pt', api_key=key))
        try:
            req = Request('https://serpapi.com/search.json?'+params, headers={'User-Agent':'FreitShop/1.0'})
            with urlopen(req, timeout=25) as response:
                data = json.load(response)
        except HTTPError as e:
            return 502, {'error': 'Chave da SerpApi inválida ou sem acesso.' if e.code in (401,403) else 'Limite de consultas atingido ou provedor indisponível. Confira sua conta SerpApi.'}
        except (URLError, TimeoutError, ValueError, OSError):
            return 502, {'error':'O provedor não respondeu corretamente. Tente novamente.'}
        if not isinstance(data, dict) or data.get('error'):
            return 502, {'error':'O provedor não concluiu a consulta. Confira a chave e a cota da SerpApi.'}
        payload = {'offers':normalize(data), 'fetchedAt':datetime.now(timezone.utc).isoformat(), 'cached':False}
        if len(CACHE)>=100: CACHE.pop(next(iter(CACHE)))
        CACHE[query.casefold()] = (time.monotonic(), payload)
        return 200, payload

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed=urlsplit(self.path)
        if parsed.path == '/healthz':
            self.send_json(200, {'ok':True}); return
        if parsed.path == '/api/stats':
            try: self.send_json(200, stats())
            except (sqlite3.Error, OSError): self.send_json(503, {'error':'Contador temporariamente indisponível.'})
            return
        if parsed.path == '/api/site-config':
            self.send_json(200, ad_config()); return
        if parsed.path == '/ads.txt':
            client = ad_config()['client']
            if not client:
                self.send_json(404, {'error':'Editor AdSense ainda não configurado.'}); return
            self.respond(200, ('google.com, '+client.removeprefix('ca-')+', DIRECT, f08c47fec0942fa0\n').encode(), 'text/plain; charset=utf-8'); return
        if parsed.path=='/api/search':
            query=parse_qs(parsed.query).get('q',[''])[0].strip()
            if not 2<=len(query)<=160:
                self.send_json(400, {'error':'Digite entre 2 e 160 caracteres.'}); return
            status, data=search(query)
            self.send_json(status,data); return
        files={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8')}
        if parsed.path not in files:
            self.send_json(404,{'error':'Não encontrado.'}); return
        filename, mime=files[parsed.path]
        content = (ROOT/filename).read_bytes()
        if filename == 'index.html':
            client = ad_config()['client']
            tag = f'<meta name="google-adsense-account" content="{client}">' if client else ''
            content = content.replace(b'<!-- ADSENSE_ACCOUNT -->', tag.encode())
            try: stats(increment=True)
            except (sqlite3.Error, OSError): pass  # Uma falha do contador não bloqueia a busca.
        self.respond(200,content,mime)
    def respond(self,status,body,mime):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.end_headers()
        try: self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError): pass
    def send_json(self,status,data):
        self.respond(status,json.dumps(data,ensure_ascii=False,allow_nan=False).encode(),'application/json; charset=utf-8')
    def log_message(self,*args): pass

if __name__=='__main__':
    print('FreitShop: http://127.0.0.1:8000 — Ctrl+C para encerrar')
    port = int(os.environ.get('PORT', '8000'))
    host = os.environ.get('HOST', '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1')
    ThreadingHTTPServer((host,port),Handler).serve_forever()
