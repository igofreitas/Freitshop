"""Admin master: senha com PBKDF2, sessões opacas e patrocinadores persistentes."""
import hashlib,hmac,os,secrets,sqlite3,time
from pathlib import Path
from http.cookies import SimpleCookie,CookieError
from urllib.parse import urlsplit
from feedback import FeedbackError
DEFAULT_HASH = '58222149dd925d0e8ce3f4e45375a3e9f7aa8ee56f364affddbc635ceeb87f99'
DEFAULT_SALT = '6e74192f33d6125f712db38118b7e73a'

def connect():
    path=Path(os.environ.get('ADMIN_DB_PATH',str(Path(__file__).resolve().parent/'data'/'admin.sqlite3')))
    path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    db.executescript('CREATE TABLE IF NOT EXISTS sponsors(id INTEGER PRIMARY KEY,name TEXT NOT NULL,url TEXT NOT NULL); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,csrf TEXT NOT NULL,expires REAL NOT NULL); CREATE TABLE IF NOT EXISTS attempts(client TEXT PRIMARY KEY,count INTEGER NOT NULL,expires REAL NOT NULL);')
    return db

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()

def session(cookie):
    jar=SimpleCookie()
    try:jar.load(cookie or '')
    except CookieError:return None
    item=jar.get('freitshop_admin')
    if not item:return None
    db=connect()
    try:return db.execute('SELECT token,csrf FROM sessions WHERE token=? AND expires>?',(token_hash(item.value),time.time())).fetchone()
    finally:db.close()

def cookie(value,age=28800):
    return 'freitshop_admin='+value+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+str(age)+('; Secure' if os.environ.get('PUBLIC_SITE_URL','').startswith('https://') else '')

def login(data,client,old_cookie):
    username=data.get('username','');password=data.get('password','')
    if not isinstance(username,str) or not isinstance(password,str) or len(password)>256:raise FeedbackError(400,'Credenciais inválidas.')
    db=connect()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE expires<?',(time.time(),))
            row=db.execute('SELECT count FROM attempts WHERE client=?',(client,)).fetchone()
            if row and row[0]>=10:raise FeedbackError(429,'Aguarde 15 minutos antes de tentar novamente.')
            db.execute('INSERT INTO attempts VALUES(?,1,?) ON CONFLICT(client) DO UPDATE SET count=count+1',(client,time.time()+900))
        expected=os.environ.get('ADMIN_PASSWORD_HASH',DEFAULT_HASH)
        salt=os.environ.get('ADMIN_PASSWORD_SALT',DEFAULT_SALT)
        candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
        if not (hmac.compare_digest(candidate,expected) and hmac.compare_digest(username.encode(),os.environ.get('ADMIN_USERNAME','igfreitasAdmin').encode())):raise FeedbackError(401,'Usuário ou senha incorretos.')
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        previous=session(old_cookie)
        with db:
            db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
            if previous:db.execute('DELETE FROM sessions WHERE token=?',(previous[0],))
            db.execute('INSERT INTO sessions VALUES(?,?,?)',(token_hash(token),csrf,time.time()+28800))
            db.execute('DELETE FROM attempts WHERE client=?',(client,))
        return {'authenticated':True,'csrf':csrf},cookie(token)
    finally:db.close()

def listing():
    db=connect()
    try:return {'items':[{'id':row[0],'name':row[1],'url':row[2]} for row in db.execute('SELECT id,name,url FROM sponsors ORDER BY id')]}
    finally:db.close()

def mutate(path,data,current,csrf):
    if not current:raise FeedbackError(401,'Entre novamente para administrar.')
    if not hmac.compare_digest(csrf,current[1]):raise FeedbackError(403,'Sessão inválida. Entre novamente.')
    db=connect()
    try:
        with db:
            if path=='/api/admin/logout':
                db.execute('DELETE FROM sessions WHERE token=?',(current[0],));return {'ok':True},cookie('',0)
            identity=data.get('id')
            if identity is not None and (type(identity) is not int or not 1<=identity<=9223372036854775807):raise FeedbackError(400,'Patrocinador inválido.')
            if path=='/api/admin/sponsors/delete':
                if identity is None:raise FeedbackError(400,'Selecione um patrocinador.')
                cursor=db.execute('DELETE FROM sponsors WHERE id=?',(identity,))
            else:
                name=data.get('name');url=data.get('url')
                if not isinstance(name,str) or not 1<=len(name.strip())<=120 or not isinstance(url,str) or len(url)>2048:raise FeedbackError(400,'Informe nome (até 120 caracteres) e link válido.')
                parsed=urlsplit(url)
                if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or any(ord(c)<=32 for c in url):raise FeedbackError(400,'Use um link HTTP ou HTTPS válido.')
                if identity is None:cursor=db.execute('INSERT INTO sponsors(name,url) VALUES(?,?)',(name.strip(),url))
                else:cursor=db.execute('UPDATE sponsors SET name=?,url=? WHERE id=?',(name.strip(),url,identity))
            if not cursor.rowcount:raise FeedbackError(404,'Patrocinador não encontrado.')
        return {'ok':True},None
    finally:db.close()
