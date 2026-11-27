"""Configuração editorial e exportação do conteúdo pelo administrador."""
import os
import re
from contextlib import closing
from urllib.parse import urlsplit

import admin
import feedback
import price_history
import visitor_tracking

DEFAULTS = {
    'title': 'Encontre e compare ofertas online',
    'intro': 'Digite o modelo completo para resultados mais precisos. Confira capacidade, cor, estado e vendedor antes de comparar.',
    'client': '', 'slot': '', 'privacyUrl': '', 'enabled': 'false'
}
ENV = {'client':'ADSENSE_CLIENT', 'slot':'ADSENSE_SLOT', 'privacyUrl':'PRIVACY_URL', 'enabled':'ADSENSE_ENABLED'}


def settings():
    values = DEFAULTS.copy()
    for key, variable in ENV.items():
        values[key] = os.environ.get(variable, values[key]).strip()
    with closing(admin.connect()) as db:
        values.update(db.execute('SELECT name,value FROM site_settings'))
    return values


def save(data):
    fields = {k: data.get(k) for k in DEFAULTS}
    if any(not isinstance(v,str) for v in fields.values()):
        raise feedback.FeedbackError(400,'Confira os campos do formulário.')
    fields = {k:v.strip() for k,v in fields.items()}
    if not 1 <= len(fields['title']) <= 120 or not 1 <= len(fields['intro']) <= 500:
        raise feedback.FeedbackError(400,'Confira o título e a descrição.')
    if not re.fullmatch(r'(ca-pub-[0-9]{16})?',fields['client']) or not re.fullmatch(r'[0-9]{0,20}',fields['slot']):
        raise feedback.FeedbackError(400,'Confira o ID do editor e do bloco de anúncios.')
    if fields['privacyUrl']:
        url = urlsplit(fields['privacyUrl'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password or len(fields['privacyUrl'])>2048:
            raise feedback.FeedbackError(400,'Informe o endereço HTTPS da política de privacidade.')
    if fields['enabled'] not in ('true','false') or (fields['enabled']=='true' and not all(fields[k] for k in ('client','slot','privacyUrl'))):
        raise feedback.FeedbackError(400,'Preencha os dados do AdSense antes de ativar os anúncios.')
    with closing(admin.connect()) as db, db:
        db.executemany('INSERT INTO site_settings(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value', fields.items())
    return {'ok':True}


def remove_comment(data):
    identity = data.get('id')
    if type(identity) is not int or not 1 <= identity <= 2**63-1:
        raise feedback.FeedbackError(400,'Comentário inválido.')
    with closing(feedback.connect()) as db, db:
        if not db.execute('DELETE FROM feedback WHERE id=?',(identity,)).rowcount:
            raise feedback.FeedbackError(404,'Comentário não encontrado.')
    return {'ok':True}


def export_content():
    # Exporta conteúdo legível, sem credenciais, sessões, IPs ou chaves.
    feedback.ready()
    with closing(feedback.connect()) as db:
        comments = [feedback.decode_row(row) for row in db.execute('SELECT * FROM feedback ORDER BY id')]
    with closing(price_history.connection()) as db:
        db.execute('BEGIN')
        offers = [dict(zip(('id','name','store','url'),row)) for row in db.execute('SELECT * FROM price_offers')]
        points = [dict(zip(('offerId','day','price','observedAt'),row)) for row in db.execute('SELECT * FROM price_observations')]
    return {'format':1,'settings':settings(),'affiliates':admin.listing(True)['items'],'sponsors':admin.listing()['items'],'comments':comments,
            'offers':offers,'observations':points,'visits':visitor_tracking.stats()}
