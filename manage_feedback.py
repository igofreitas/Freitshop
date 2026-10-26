"""Administração local pelo operador com acesso ao servidor e às chaves."""
import argparse
import feedback

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Moderação e rotação de criptografia do feedback.')
    sub=parser.add_subparsers(dest='command',required=True)
    delete=sub.add_parser('delete',help='Remover um feedback público pelo ID retornado pela API.')
    delete.add_argument('id',type=int)
    sub.add_parser('rotate',help='Recriptografar todos os registros usando a chave ativa; mantenha as chaves antigas durante a operação.')
    args=parser.parse_args()
    db=feedback.connect()
    try:
        with db:
            if args.command=='delete':
                result=db.execute('DELETE FROM feedback WHERE id=?',(args.id,))
                print('Registros removidos:',result.rowcount)
            else:
                db.execute('BEGIN IMMEDIATE')
                rows=db.execute('SELECT * FROM feedback').fetchall()
                for row in rows:
                    data=feedback.decode_row(row)
                    key,nonce,ciphertext=feedback.encrypt(row[1],{'rating':data['rating'],'comment':data['comment']})
                    db.execute('UPDATE feedback SET key_id=?,nonce=?,ciphertext=? WHERE id=?',(key,nonce,ciphertext,row[0]))
                print('Registros recriptografados:',len(rows))
    finally:db.close()
