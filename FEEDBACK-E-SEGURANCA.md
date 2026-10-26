> Atualização: consulte CORRECOES.md. O contador agora usa um cookie por navegador/dia; a ativação e a chave do feedback são automáticas em instalações novas. As instruções antigas por IP ou de configuração manual obrigatória abaixo foram substituídas.

# Avaliações sem cadastro

A área de feedback fica no final da página, sem botões de login, cadastro, Google ou recuperação de senha. A avaliação é enviada anonimamente, com nota inteira de 1 a 5 e comentário entre 1 e 500 caracteres. A validação ocorre no navegador e no servidor. A contagem de caracteres usa pontos de código Unicode.

## Atualização

Substitua `index.html`, `app.js`, `feedback.js`, `feedback.py`, `server.py` e `requirements.txt`. Adicione `visitor_tracking.py`. Preserve `price_history.py`, bancos e chaves existentes. Instale dependências com `pip install -r requirements.txt` e publique novamente. O SDK Firebase deixou de ser uma dependência.

As variáveis FIREBASE_WEB_CONFIG e FIREBASE_SERVICE_ACCOUNT_JSON não são mais usadas e podem ser removidas da configuração desta aplicação. FEEDBACK_ID_KEY também não é mais necessária. Contas que já existam no Firebase não são apagadas por esta atualização.

## Configuração mantida para proteger os comentários

- FEEDBACK_ENABLED=true para habilitar o formulário.
- PUBLIC_SITE_URL com a origem HTTPS exata do site (sem caminho). HTTP é aceito somente para localhost/127.0.0.1.
- FEEDBACK_DB_PATH em disco persistente, por exemplo /var/data/feedback.sqlite3.
- FEEDBACK_KEYS_JSON e FEEDBACK_ACTIVE_KEY: mantenha os valores existentes. Não troque as chaves ao publicar.

Se ainda não tem chaves, execute `python generate_feedback_keys.py` localmente e copie as duas variáveis de `.feedback-secrets.json` para os segredos da hospedagem. Não publique esse arquivo. Se ele já existir, o gerador não o sobrescreve. As chaves continuam necessárias; não há login nem necessidade de criar um projeto Firebase.

## Dados e proteção

Comentários e estrelas são públicos como Visitante, inclusive registros anteriores. A atualização preserva o banco e consegue ler avaliações antigas com as chaves originais. Nenhum comentário novo afirma que a pessoa foi verificada.

Os novos comentários recebem identificadores aleatórios, sem vínculo com uma conta. Conteúdo e estrelas continuam criptografados em disco com AES-256-GCM, nonce aleatório e autenticação dos dados. Não há criptografia ponta a ponta: o servidor descriptografa para exibir a avaliação publicamente.

Há limite de seis envios por IP por minuto, usando HMAC diário, sem salvar o IP bruto. Esse controle depende da configuração correta dos proxies (veja VISITAS-UNICAS.md) e não elimina spam distribuído. A origem da solicitação é verificada, o corpo JSON é limitado a 8 KiB e SQL é parametrizado. Comentários são exibidos como texto, nunca HTML executável.

Sem conta autenticada, não há edição/exclusão pública por autor: essas rotas foram removidas para impedir que visitantes alterem avaliações de terceiros. O operador pode remover um comentário pelo seu ID público usando `python manage_feedback.py delete ID` no ambiente do servidor. Mantenha um canal de contato na política de privacidade para solicitações de remoção.

A rotação continua disponível: preserve as chaves antigas, adicione a nova chave AES de 32 bytes a FEEDBACK_KEYS_JSON, altere FEEDBACK_ACTIVE_KEY e execute `python manage_feedback.py rotate`. A operação é transacional. Proteja backups e só retire chaves antigas depois da migração e revisão dos backups.

Atualize sua política de privacidade para refletir avaliações públicas sem cadastro e identificação técnica por IP/HMAC para estatísticas e controle de abuso. Registros de hospedagem podem seguir regras próprias. O código não oferece garantia absoluta de segurança nem substitui controles de infraestrutura.

## Verificação

`python -m unittest discover -v` executa os testes do servidor. `node test_feedback_client.cjs` verifica o formulário sem login com rede simulada. O envio HTTP anônimo, limite de caracteres/estrelas, criptografia, limitação de envios e leitura de registros anteriores foram testados. O site publicado não foi alterado automaticamente.
