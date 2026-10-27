# Contador persistente no PostgreSQL do Render

## Aplicar

Esta versão usa PostgreSQL para o contador quando DATABASE_URL está definida. Sem essa variável, continua usando SQLite local para desenvolvimento. Se DATABASE_URL estiver definida e houver falha de conexão, o contador retorna indisponível: nunca troca silenciosamente para SQLite nem retorna zero como se fosse um banco novo.

1. Envie ao GitHub todos os arquivos atualizados, incluindo postgres_counter.py, visitor_tracking.py, server.py, requirements.txt e migrate_counter.py.
2. No Web Service do Render, configure DATABASE_URL em Environment com a conexão do seu PostgreSQL. Use a Internal Database URL se banco e serviço estiverem na mesma região/rede Render; fora dela, use a URL externa com TLS conforme o provedor.
3. O Build Command precisa instalar requirements.txt: `pip install -r requirements.txt`. Se os arquivos estiverem na subpasta freitshop, use essa pasta como Root Directory, ou mantenha os caminhos adequados já usados no seu serviço.
4. Start Command: `python server.py` (no diretório dos arquivos). Faça o deploy.
5. Abra `/api/stats` no domínio do site e confira `"storage": "postgresql"`. Esse campo confirma que o contador usa PostgreSQL. A resposta não expõe credenciais.

Não coloque DATABASE_URL no GitHub ou no JavaScript. Não é necessário me enviar essa URL.

## Chave e contagem

O banco cria automaticamente as tabelas freitshop_visit_totals, freitshop_daily_visitors e freitshop_counter_settings. A última guarda uma chave aleatória persistente para assinar o cookie e proteger os identificadores. Assim, ela não muda quando o Render recria os arquivos locais. Se VISITOR_HASH_KEY já está definida, preserve seu valor: a chave configurada deve coincidir com a persistida, caso contrário a aplicação recusa a configuração.

O servidor registra no máximo uma visita por navegador por dia, em uma transação. O total soma os dias. À meia-noite de Brasília, hoje começa em zero; páginas abertas não criam visitas automaticamente. Atualizações periódicas apenas consultam os totais. Novo deploy usando o mesmo PostgreSQL conserva os dados.

## Importar histórico SQLite existente

Se o banco antigo já foi apagado e não existe backup, seus números não podem ser recuperados por esta atualização.

Se existe backup, faça a migração ANTES de liberar tráfego da versão PostgreSQL. Pause gravações na versão antiga e preserve os dois arquivos: access.sqlite3 e access.visitors.key (ou seus caminhos personalizados). O destino PostgreSQL deve estar vazio de visitas. Não execute a importação a cada deploy.

Em um ambiente que tenha esses arquivos e acesso ao PostgreSQL, instale as dependências, configure DATABASE_URL somente no ambiente e execute:

```sh
python migrate_counter.py --sqlite /caminho/access.sqlite3 --key /caminho/access.visitors.key
```

O script copia totais diários, identificadores e chave original em uma transação. Não apaga o SQLite. Repetir o mesmo backup não soma os valores duas vezes. Se o PostgreSQL já tiver visitas ou outra importação, o script cancela sem sobrescrever. Nesse caso é necessária uma análise dos dois históricos antes de mesclar.

Para rodar a migração do seu computador, use a conexão externa autorizada pelo provedor; a conexão interna do Render não é acessível de fora da rede privada.

## Escopo e persistência

Esta atualização migra SOMENTE o contador. Patrocinadores, feedback e histórico de preços ainda usam SQLite e precisam de disco persistente ou de migração própria. DATABASE_URL não migra automaticamente esses outros módulos. A chave antispam compartilhada passa a vir do PostgreSQL, mas os registros desses módulos continuam locais.

O próprio PostgreSQL precisa estar em um plano que permaneça ativo, com backups. No Render, o PostgreSQL gratuito tem prazo de expiração; confira o plano do banco. Esta integração não impede expiração, exclusão manual ou troca para outro banco vazio.

## Testes

`python -m unittest discover -v` executa os testes locais. Para testar PostgreSQL real, configure TEST_POSTGRES_URL com um banco de testes onde o usuário possa criar schemas e execute `python -m unittest test_postgres_counter -v`. Os testes usam schemas isolados temporários e removem apenas esses schemas.
