# Atualização: contador e preparação para AdSense

## Instalar no site existente

Faça backup da versão atual. Substitua `index.html`, `app.js` e `server.py` pelos arquivos deste pacote e publique novamente. Preserve configurações e personalizações feitas diretamente no seu repositório: esta atualização parte do pacote enviado nesta conversa, não de uma leitura do site publicado.

Mantenha `SERPAPI_KEY` nas variáveis da hospedagem. Não há chave incluída no pacote. Inicie com `python server.py`. O servidor reconhece `PORT` da hospedagem e utiliza 0.0.0.0 automaticamente quando ela existe. Para monitoramento de disponibilidade use `/healthz`, não `/`, evitando inflar o contador.

## Contador

O rodapé exibe o total desde a instalação e o total do dia em UTC−3. Conta requisições GET que servem `/` ou `/index.html`, inclusive recarregamentos e robôs. Não mede pessoas únicas, não filtra tráfego fraudulento e não é uma métrica de impressões do AdSense. Não usa cookies, IPs nem identificadores de visitantes. Serviços de hospedagem e recursos de terceiros podem ter seus próprios registros.

Os números são gravados em SQLite e sobrevivem ao reinício do processo somente se o arquivo for preservado. O banco começa em zero; acessos anteriores não são recuperados.

### Persistência no Render

O plano gratuito perde arquivos locais ao reiniciar/republicar/suspender o serviço. Para este contador durar, configure um serviço com disco persistente e monte, por exemplo, em `/var/data`. Então defina:

```
STATS_DB_PATH=/var/data/freitshop-access.sqlite3
```

Não basta definir o caminho: o disco precisa estar criado e montado. Esse recurso pode ter custo. Este projeto usa SQLite em uma instância; não possui integração com Postgres ou sincronização entre várias instâncias. Em hospedagem gratuita sem disco persistente, use outro serviço de estatísticas ou adapte o contador para um banco externo antes de tratá-lo como acumulado permanente.

Faça backup do banco com o servidor parado ou com a API de backup do SQLite. Não envie o banco ao GitHub. `/api/stats` só lê os totais; o arquivo SQLite não é servido pela aplicação.

## Preparar o AdSense

1. Cadastre seu site em https://adsense.google.com/start/ e siga a revisão do Google. Receita e aprovação não são garantidas. Um catálogo externo sozinho não garante qualidade suficiente; desenvolva conteúdo próprio útil, como guias, análises e critérios de comparação.
2. Obtenha seu ID público de editor no formato `ca-pub-` seguido de 16 dígitos. Configure `ADSENSE_CLIENT` na hospedagem.
3. A aplicação passa a fornecer a meta tag de verificação e `/ads.txt`. Use uma das opções compatíveis oferecidas pelo painel, como a meta tag. Se o Google fornecer instruções diferentes para sua conta, siga-as.
4. Crie um bloco de anúncios de display responsivo e copie seu número `data-ad-slot` para `ADSENSE_SLOT`.
5. Publique uma política de privacidade que descreva suas práticas reais, terceiros, publicidade, cookies, contato e opções do visitante. Configure `PRIVACY_URL` com o endereço HTTPS dessa página. Este pacote não publica uma política jurídica pronta nem inventa dados do responsável.
6. Configure o gerenciamento de consentimento aplicável ao seu público. Para anúncios personalizados a usuários do EEE, Reino Unido e Suíça, siga a exigência do Google de CMP certificada integrada ao TCF. Use a integração oficial da CMP ou as opções compatíveis de Privacidade e mensagens no AdSense; este pacote NÃO inclui uma CMP. Um banner próprio ou este código, sozinho, não substitui essa configuração. Revise o momento de carregamento do anúncio conforme a integração escolhida, inclusive bloqueio e retirada de consentimento.
7. Somente depois da aprovação e da preparação acima, configure `ADSENSE_ENABLED=true` e publique novamente. Antes disso o script publicitário não é carregado. Não ative para teste de cliques.

Variáveis (os valores abaixo são descrições, não credenciais válidas):

| Variável | O que informar |
| --- | --- |
| ADSENSE_CLIENT | Seu ca-pub- com 16 dígitos |
| ADSENSE_SLOT | Número do bloco responsivo |
| PRIVACY_URL | Endereço HTTPS da sua política publicada |
| ADSENSE_ENABLED | true após concluir aprovação/privacidade; false para desligar |
| STATS_DB_PATH | Caminho do arquivo em disco persistente |

O bloco aparece ao final do conteúdo, separado dos botões de ofertas e identificado como Publicidade. A configuração inválida mantém anúncios desligados. O script do Google é carregado uma única vez; filtros e comparações não geram atualizações artificiais de anúncios. O Google pode não preencher o espaço mesmo com integração correta. Bloqueadores de anúncios também podem impedir a exibição.

Não clique nos próprios anúncios, não peça cliques a amigos e não compre tráfego artificial. O contador não determina receita; use os relatórios do AdSense. A aplicação não altera configurações da sua conta e não solicita aprovação automaticamente.

## Validação

Nove testes Python passam, incluindo concorrência no contador, persistência entre conexões, rotas, configuração dos anúncios e testes anteriores de busca. Sintaxe JavaScript verificada. Exibição real de anúncios e consentimento dependem de sua conta e não foram testados. A publicação no seu site ainda precisa ser feita por você.

## Referências oficiais

- https://support.google.com/adsense/answer/9724?hl=pt-BR
- https://support.google.com/adsense/answer/7584263?hl=en
- https://support.google.com/adsense/answer/10502938?hl=en
- https://support.google.com/adsense/answer/13554116?hl=en
- https://render.com/docs/free
- https://render.com/docs/disks
