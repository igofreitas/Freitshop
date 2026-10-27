"""Execute fora do tráfego: python migrate_counter.py --sqlite backup.db --key backup.key"""
import argparse,json,os
from postgres_counter import migrate,CounterStorageError
if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Importa contador SQLite em PostgreSQL vazio sem somar duas vezes.')
    parser.add_argument('--sqlite',required=True);parser.add_argument('--key',required=True)
    args=parser.parse_args()
    if not os.environ.get('DATABASE_URL','').strip():parser.error('Defina DATABASE_URL no ambiente antes de importar.')
    try:print(json.dumps(migrate(args.sqlite,args.key),ensure_ascii=False))
    except Exception:raise SystemExit('Importação não concluída. Confira o backup, a chave, a conexão e se o destino está vazio. Nenhum dado parcial é gravado.') from None
