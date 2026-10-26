> Contador atualizado: consulte CONTADOR-PERSISTENTE.md para sincronização entre dispositivos e preservação do histórico em atualizações.

> Atualização: consulte CORRECOES.md. O contador agora usa um cookie por navegador/dia; a ativação e a chave do feedback são automáticas em instalações novas. As instruções antigas por IP ou de configuração manual obrigatória abaixo foram substituídas.

# FreitShop — busca e comparação de ofertas

Versão adaptada do HTML enviado. Mantém a identidade visual escura, roxa e vermelha, substituindo o catálogo fictício por consulta ao Google Shopping via SerpApi.

## Executar

1. Instale Python 3.10 ou superior e extraia este ZIP.
2. Crie uma conta em https://serpapi.com/ e obtenha sua chave. Consulte os limites e preços do serviço; o projeto não inclui créditos nem uma chave.
3. Abra um terminal na pasta que contém server.py.
4. Configure a chave e inicie:

Windows PowerShell:

```powershell
$env:SERPAPI_KEY="SUA_CHAVE"
python server.py
```

Linux ou macOS:

```bash
export SERPAPI_KEY='SUA_CHAVE'
python3 server.py
```

5. Acesse http://127.0.0.1:8000 no navegador. Não abra o HTML por duplo clique.

Instale as dependências com `python -m pip install -r requirements.txt` para usar a criptografia do feedback. A interface usa Tailwind e Font Awesome por CDN, por isso precisa de internet. A chave fica apenas no ambiente do servidor; nunca coloque a chave no HTML ou no JavaScript.

## Uso

Digite marca e modelo, preferencialmente capacidade e versão, e pressione Enter ou a lupa. Selecione uma loja, ajuste o preço máximo e ordene os resultados. Marque até quatro ofertas e clique em Comparar. Limpar restaura os filtros da consulta atual. Uma nova busca limpa a seleção anterior.

## O que os resultados significam

- São ofertas retornadas pelo Google Shopping, não uma consulta direta a todas as lojas. A presença de Amazon, Mercado Livre, Magalu ou qualquer outra loja depende do provedor e da pesquisa.
- Resultados podem conter variantes, acessórios e produtos diferentes. Não há agrupamento automático que afirme serem o mesmo produto. Confira modelo, capacidade, condição e vendedor antes de comparar.
- O menor preço é somente o menor entre as ofertas exibidas. A diferença na tabela usa apenas as ofertas selecionadas. Frete, cupons, parcelamento e disponibilidade não são verificados no checkout.
- Valores sem indicação de reais ou sem preço numérico válido são descartados. Não se utiliza o campo de parcelas como preço total.
- Os links podem abrir a página intermediária do Google Shopping. O botão não garante link direto ao varejista.
- A data exibida indica a consulta ao provedor, não o instante em que a loja alterou o preço. Consultas iguais usam cache local por até cinco minutos. Apenas a página de resultados retornada pelo provedor é exibida, sem paginação.
- Histórico inventado e alertas de e-mail simulados foram retirados. Esta versão não envia e-mails. Agora registra histórico real a partir das consultas: veja BLACK-FRIDAY.md.

## Arquivos

- index.html: interface adaptada.
- app.js: consulta, filtros, seleção e comparação.
- server.py: integração SerpApi e servidor local com biblioteca padrão Python.
- test_server.py: testes com respostas simuladas; execute `python -m unittest -v`.

Sem PORT configurada, o servidor escuta em 127.0.0.1. Na hospedagem, reconhece PORT e usa 0.0.0.0. Para publicação será necessário um ambiente de hospedagem Python, HTTPS, autenticação/controle de acesso e limites de uso apropriados para proteger a cota da API.

## Validação e limites

Os testes verificam normalização de preços, exclusão de moedas estrangeiras e links inseguros, cache, falta de chave e falhas do provedor. Uma consulta real requer sua chave e não foi validada nesta entrega.

Documentação da integração: https://serpapi.com/google-shopping-api e https://serpapi.com/shopping-results


## Contador e monetização

Leia CONTADOR-E-ADSENSE.md antes de atualizar o site. Inclui persistência do contador, configuração de anúncios e etapas pendentes de aprovação e consentimento.

## Compare o Black Friday

Leia BLACK-FRIDAY.md. A atualização requer o novo price_history.py além de index.html, app.js e server.py. O histórico começa nas consultas após instalar, sem preços anteriores inventados.

## Feedback e visitas

A versão atual permite avaliações sem login e conta uma visita por IP por dia. Leia FEEDBACK-E-SEGURANCA.md e VISITAS-UNICAS.md. Não é necessário Firebase. Mantenha as chaves de criptografia e o armazenamento persistente.
