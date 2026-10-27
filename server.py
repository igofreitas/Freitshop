"""FreitShop: Python 3.10+. Instale requirements.txt para o módulo de feedback."""
import json, os, time, math, threading, sqlite3, re, html
import price_history
import feedback
import admin
import visitor_tracking
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

def stats(increment=False, visitor_id=None, now=None):
    if increment and visitor_id is None: raise ValueError('Identificador obrigatório para registrar uma visita.')
    return visitor_tracking.stats(visitor_id if increment else None, now)

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
    for offer in result: offer['historyId'] = price_history.offer_key(offer)
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
        try:
            price_history.record(payload['offers'], payload['fetchedAt'])
            payload['historySaved'] = True
        except (sqlite3.Error, OSError):
            payload['historySaved'] = False
        if len(CACHE)>=100: CACHE.pop(next(iter(CACHE)))
        CACHE[query.casefold()] = (time.monotonic(), payload)
        return 200, payload

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(20)

    def feedback_operation(self, operation):
        try:
            self.send_json(200, operation())
        except feedback.FeedbackError as e:
            self.send_json(e.status, {'error':str(e)})
        except (ImportError,sqlite3.Error,OSError,ValueError):
            self.send_json(503, {'error':'Feedback temporariamente indisponível. Verifique a configuração do serviço.'})

    def admin_operation(self,path):
        try:
            feedback.check_origin(self.headers.get('Origin',''),self.headers.get('Host',''))
            lengths=self.headers.get_all('Content-Length') or []
            if len(lengths)!=1 or not lengths[0].isdigit() or self.headers.get('Transfer-Encoding') or not 1<=int(lengths[0])<=8192:
                raise feedback.FeedbackError(400,'Solicitação inválida.')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise feedback.FeedbackError(415,'Envie JSON.')
            data=json.loads(self.rfile.read(int(lengths[0])))
            if not isinstance(data,dict):raise feedback.FeedbackError(400,'Dados inválidos.')
            if path=='/api/admin/login':
                client=visitor_tracking.daily_token(visitor_tracking.client_ip(self.client_address[0],self.headers),purpose='admin')
                result,cookie=admin.login(data,client,self.headers.get('Cookie',''))
            else:result,cookie=admin.mutate(path,data,admin.session(self.headers.get('Cookie','')),self.headers.get('X-CSRF-Token',''))
            self.respond(200,json.dumps(result).encode(),'application/json; charset=utf-8',cookie)
        except feedback.FeedbackError as e:self.send_json(e.status,{'error':str(e)})
        except (ValueError,sqlite3.Error,OSError):self.send_json(503,{'error':'Não foi possível concluir. Confira os dados e o armazenamento do servidor.'})

    def do_POST(self):
        path=urlsplit(self.path).path
        if path in ('/api/admin/login','/api/admin/logout','/api/admin/sponsors','/api/admin/sponsors/delete'):
            self.admin_operation(path);return
        if path == '/api/visit':
            try:
                identity,cookie=visitor_tracking.browser_identity(self.headers.get('Cookie',''))
                data=stats(True,visitor_id=identity)
                self.respond(200,json.dumps(data).encode(),'application/json; charset=utf-8',cookie)
            except (sqlite3.Error,OSError,ValueError):
                self.send_json(503,{'error':'Não foi possível registrar a visita. Verifique o armazenamento do servidor.'})
            return
        if path != '/api/feedback':
            self.send_json(404, {'error':'Não encontrado.'});return
        def mutate():
            feedback.ready()
            feedback.check_origin(self.headers.get('Origin',''),self.headers.get('Host',''))
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                raise feedback.FeedbackError(415,'Envie dados JSON.')
            sizes=self.headers.get_all('Content-Length') or []
            if len(sizes)!=1 or not sizes[0].isdigit() or self.headers.get('Transfer-Encoding'):
                raise feedback.FeedbackError(400,'Tamanho de solicitação inválido.')
            length=int(sizes[0])
            if not 1<=length<=8192: raise feedback.FeedbackError(413,'Solicitação muito grande ou vazia.')
            ip=visitor_tracking.client_ip(self.client_address[0],self.headers)
            rate_id=visitor_tracking.daily_token(ip,purpose='feedback')
            try:
                data=json.loads(self.rfile.read(length).decode('utf-8'))
            except (ValueError,UnicodeError): raise feedback.FeedbackError(400,'JSON inválido.') from None
            return feedback.submit_anonymous(data,rate_id)
        self.feedback_operation(mutate)

    def do_GET(self):
        parsed=urlsplit(self.path)
        if parsed.path=='/api/sponsors':
            self.feedback_operation(admin.listing);return
        if parsed.path=='/api/admin/session':
            def state():
                current=admin.session(self.headers.get('Cookie',''))
                return {'authenticated':bool(current),'csrf':current[1] if current else None}
            self.feedback_operation(state);return
        if parsed.path == '/api/feedback-config':
            self.send_json(200,feedback.public_config());return
        if parsed.path == '/api/feedback':
            def read_feedback():
                before=parse_qs(parsed.query).get('before',[None])[0]
                if before is not None:
                    if not before.isdigit() or not 1<=int(before)<=9223372036854775807:
                        raise feedback.FeedbackError(400,'Página inválida.')
                    before=int(before)
                return feedback.listing(before)
            self.feedback_operation(read_feedback);return
        if parsed.path == '/healthz':
            self.send_json(200, {'ok':True}); return
        if parsed.path == '/api/price-history':
            params = parse_qs(parsed.query)
            identity = params.get('offer',[''])[0]
            months_text = params.get('months',['4'])[0]
            if not re.fullmatch(r'[0-9a-f]{64}', identity) or months_text not in ('1','2','3','4'):
                self.send_json(400, {'error':'Oferta ou período inválido.'}); return
            try:
                history = price_history.get_history(identity, int(months_text))
                if history is None: self.send_json(404, {'error':'Ainda não há registros para esta oferta.'})
                else: self.send_json(200, history)
            except (sqlite3.Error, OSError): self.send_json(503, {'error':'Não foi possível ler o histórico. Verifique o armazenamento do servidor.'})
            return
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
        files={'/counter.js':('counter.js','text/javascript; charset=utf-8'),'/admin.js':('admin.js','text/javascript; charset=utf-8'),'/feedback.js':('feedback.js','text/javascript; charset=utf-8'),'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8')}
        if parsed.path not in files:
            self.send_json(404,{'error':'Não encontrado.'}); return
        filename, mime=files[parsed.path]
        content = (ROOT/filename).read_bytes()
        if filename == 'index.html':
            client = ad_config()['client']
            tag = f'<meta name="google-adsense-account" content="{client}">' if client else ''
            content = content.replace(b'<!-- ADSENSE_ACCOUNT -->', tag.encode())
            try:
                counts=stats()
                label=f"{counts['total']:,} no total • {counts['today']:,} hoje".replace(',','.')
                snapshot=html.escape(json.dumps(counts),quote=True)
                content=content.replace(b'id="accessCounter"',('id="accessCounter" data-server-value="true" data-stats="'+snapshot+'"').encode())
                content=content.replace('>Carregando…</p>'.encode(),('>'+label+'</p>').encode(),1)
            except (sqlite3.Error,OSError,ValueError):pass
        self.respond(200,content,mime)
    def respond(self,status,body,mime,cookie=None):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        if cookie:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        if os.environ.get('PUBLIC_SITE_URL','').startswith('https://'):
            self.send_header('Strict-Transport-Security','max-age=31536000')
        self.send_header('Content-Security-Policy',"frame-ancestors 'none'; object-src 'none'; base-uri 'self'")
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
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
    cleanup_stop = price_history.start_daily_cleanup()
    try:
        ThreadingHTTPServer((host,port),Handler).serve_forever()
    finally:
        cleanup_stop.set()
