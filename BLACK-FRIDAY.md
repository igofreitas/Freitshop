# Compare o Black Friday

## Instalação

Faça backup do projeto publicado. Atualize `index.html`, `app.js`, `server.py` e adicione o novo arquivo `price_history.py` na mesma pasta. Publique novamente. Não remova configurações da SerpApi, AdSense ou dados existentes. Esta versão parte do pacote entregue na conversa; alterações que você fez fora dele precisam ser preservadas ao atualizar.

## O que o visitante verá

1. Clique em **Compare o Black Friday**.
2. Digite marca e modelo na busca e pressione Enter ou a lupa.
3. As ofertas aparecem com nome do produto, loja e preço. Os filtros de loja, preço e ordenação também funcionam nesta seção.
4. Selecione uma oferta para abrir preço atual anunciado na consulta, link de origem e gráfico de histórico daquela oferta/loja.
5. Escolha 1, 3, 6 ou 12 meses. O padrão é 6 meses. Há também uma tabela acessível de datas e preços.

O botão alterna entre a seção Black Friday e os cards normais. A seção é uma ferramenta de comparação, não uma afirmação de que as ofertas possuem desconto ou participam da Black Friday.

## Limitação essencial: histórico real começa na instalação

A integração existente da SerpApi retorna preços de busca, não seis meses de histórico. O projeto NÃO inventa dados anteriores, não usa preços riscados como histórico e não recupera automaticamente preços antigos.

A cada consulta bem-sucedida ao provedor, o servidor guarda as ofertas retornadas. Uma resposta em cache não cria uma nova observação. Para cada oferta, mantém o último preço observado de cada dia em UTC−3. Não há agendador: dias sem consultas ficam sem registros. A coleta não implica monitoramento contínuo nem garantia de disponibilidade da loja.

No primeiro dia aparece um único ponto. Com consultas em outros dias, o gráfico passa a ter mais pontos. O período selecionado define a janela do gráfico; não significa que existam dados em todos os meses dessa janela. A linha tracejada conecta observações e não estima preços nos intervalos. O menor/maior exibido refere-se somente aos registros disponíveis.

Para mostrar seis meses imediatamente, seria necessário contratar/integrar uma fonte que forneça histórico real por produto e loja, ou importar um conjunto de observações verificadas. Essa integração/importação não está incluída.

A identificação considera título, loja, link de origem e condição. Variações desses campos podem iniciar outro histórico. O código não mistura ofertas por semelhança de nome. Google Shopping pode trazer páginas intermediárias; não há garantia de identidade imutável ou de mesmo vendedor dentro de um marketplace. Frete, cupons e condições de pagamento não estão normalizados no histórico.

## Salvar permanentemente

Por padrão o histórico usa o mesmo banco SQLite do contador. Se `STATS_DB_PATH` já aponta para um disco persistente, não precisa configurar um segundo caminho. As tabelas são adicionadas automaticamente, preservando o contador existente.

Se preferir separar, configure `PRICE_HISTORY_DB_PATH` com um caminho em disco persistente, por exemplo:

```
PRICE_HISTORY_DB_PATH=/var/data/freitshop-prices.sqlite3
```

É necessário montar realmente o disco na hospedagem. O Render gratuito não preserva arquivos locais após reinícios/republicações/suspensões; sem armazenamento persistente, o histórico será perdido. Não envie os bancos ao GitHub nem os substitua durante publicações. O projeto usa uma instância SQLite, não um banco remoto ou sincronizado entre servidores.

Se o banco falhar, a busca continua e a seção informa ausência/falha do histórico. Não exibe dados inventados para compensar a falha.

## Testes

Execute `python -m unittest discover -v` na pasta do projeto. Há testes de isolamento por oferta e loja, substituição do último registro diário, limites de meses (incluindo fim de mês), ausência de histórico e validação da API. A pesquisa real continua dependendo da chave SerpApi configurada no servidor.
