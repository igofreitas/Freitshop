"""Execute localmente. Não envia segredos à internet e não os imprime no terminal."""
import base64,json,os,secrets
from pathlib import Path

if __name__=='__main__':
    target=Path('.feedback-secrets.json')
    values={
        'FEEDBACK_KEYS_JSON':json.dumps({'v1':base64.b64encode(secrets.token_bytes(32)).decode()}),
        'FEEDBACK_ACTIVE_KEY':'v1'
    }
    try:
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as out:json.dump(values,out,indent=2)
    except FileExistsError:
        raise SystemExit('O arquivo já existe. Preserve suas chaves; não as substitua sem migração.')
    print('Chaves criadas em .feedback-secrets.json. Guarde em local seguro e configure as variáveis da hospedagem. Não envie ao GitHub nem compartilhe esse arquivo.')
