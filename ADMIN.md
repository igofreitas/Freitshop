# Administração e patrocinadores

Substitua os arquivos do pacote, preservando a pasta data e as variáveis de ambiente. Reinicie o servidor Python. Esta atualização exige server.py, admin.py, admin.js, app.js e index.html; trocar somente o HTML não ativa o painel.

No final da página, em Administração, entre com o usuário igfreitasAdmin e a senha fornecida na solicitação desta atualização. O servidor inclui somente um hash PBKDF2 com sal aleatório; a senha não é enviada no HTML/JavaScript nem armazenada em texto no pacote.

Após entrar, use Nome do patrocinador e Link (URL) para adicionar. Editar preenche o formulário; Salvar alterações atualiza o registro. Remover pede confirmação. A seção Patrocinadores fica acima da administração e mostra links públicos em nova aba. Sem patrocinadores, ela fica oculta. O feedback, os créditos do criador e o Instagram foram preservados.

Os registros ficam em data/admin.sqlite3 (ou ADMIN_DB_PATH). Use disco persistente para manter os patrocinadores após reinícios e novos deploys. A sessão dura oito horas, usa cookie HttpOnly/SameSite=Strict e é revogada ao sair. PUBLIC_SITE_URL deve corresponder à origem HTTPS pública do site; quando configurado com HTTPS, o cookie recebe Secure. Mantenha HTML e API na mesma origem e use HTTPS na hospedagem.

Para alterar credenciais sem editar código, defina ADMIN_USERNAME, ADMIN_PASSWORD_HASH e ADMIN_PASSWORD_SALT no servidor. O hash é PBKDF2-HMAC-SHA256, 600000 iterações, saída hexadecimal de 32 bytes, sal hexadecimal de 16 bytes. Ao mudar senha, encerre sessões existentes apagando somente as linhas da tabela sessions com o serviço parado, preservando sponsors.

Testes: python -m unittest discover -v. O teste do login real exige TEST_ADMIN_PASSWORD definida apenas no ambiente de testes.
