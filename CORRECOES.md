# Como aplicar esta atualização

1. Faça backup da pasta data e das configurações do servidor.
2. Substitua os arquivos do projeto pelo conteúdo deste ZIP, preservando data e as variáveis de ambiente existentes.
3. No diretório freitshop, execute `python -m pip install -r requirements.txt` e reinicie com `python server.py` (ou reinicie o serviço na hospedagem).
4. Abra o endereço do servidor, por exemplo http://127.0.0.1:8000. Não abra index.html diretamente nem use apenas hospedagem estática. HTML, JavaScript e /api/* precisam estar na mesma origem.
5. Se FEEDBACK_ENABLED estiver definido como false, altere para true. Se PUBLIC_SITE_URL estiver configurado, use exatamente o endereço público correto, sem caminho ou barra final.

Em instalações novas, o feedback já vem habilitado e cria uma chave AES-256-GCM privada automaticamente em data/feedback.key. Não apague essa chave: sem ela, os comentários não podem ser decifrados. Preserve data em disco persistente e faça backup protegido. Chaves manuais FEEDBACK_KEYS_JSON e FEEDBACK_ACTIVE_KEY continuam funcionando. Se já existe um banco criptografado, restaure suas chaves originais; a atualização não substitui uma chave perdida.

As avaliações continuam públicas, sem cadastro, com 1 a 5 estrelas e até 500 caracteres. A criptografia protege o armazenamento, não esconde comentários publicados. Use HTTPS em produção. Um erro de dependência/configuração aparece no formulário; não é reportado como envio bem-sucedido.

Contador: dois navegadores no mesmo IP contam separados. Atualizar a página não conta novamente no mesmo dia. O total antigo é mantido. Veja VISITAS-UNICAS.md para limites e migração.
