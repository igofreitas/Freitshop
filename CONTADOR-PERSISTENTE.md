# Contador sincronizado e persistente

## Comportamento

- PC e celular consultam o mesmo total do servidor a cada 5 segundos enquanto a página está visível. Uma diferença momentânea durante esses 5 segundos é normal.
- As consultas periódicas não geram visitas. Cada navegador conta uma vez por dia (UTC−3). Outro aparelho/navegador conta separadamente, mesmo no mesmo IP.
- Total = soma histórica das visitas diárias registradas. Hoje = visitas únicas por navegador no dia atual. Não são usuários simultaneamente online nem número de recarregamentos.
- O número salvo no servidor já vem no HTML. O navegador também mantém o último resultado para exibi-lo durante reconexões, identificado como valor anterior; esse cache não calcula nem aumenta a contagem.
- Ao mudar de dia, o total é preservado e a contagem de hoje começa novamente. Páginas que continuam abertas registram a presença naquele novo dia uma única vez.

## Aplicar sem perder o histórico

1. Faça backup de `data/access.sqlite3` e `data/access.visitors.key` antes de atualizar. Se STATS_DB_PATH ou VISITOR_KEY_FILE já estiver configurado, preserve os arquivos desses caminhos.
2. Substitua os arquivos de código deste ZIP, incluindo counter.js, app.js, index.html, server.py e visitor_tracking.py. Não apague nem substitua a pasta data. Reinicie o mesmo serviço Python, com as mesmas variáveis de ambiente.
3. Todos os aparelhos devem abrir o mesmo site publicado. Não compare uma instalação local do computador com outra hospedada: cada instalação tem seu próprio banco.

## Hospedagem com disco persistente

SQLite mantém o total após reiniciar o processo. Para manter também após novos deploys, a hospedagem precisa conservar o disco. Em hospedagem com sistema de arquivos temporário, nenhum arquivo local garante isso sozinho.

Monte um disco persistente e defina, por exemplo, `FREITSHOP_DATA_DIR=/var/data/freitshop`. Essa variável configura o diretório do contador; `STATS_DB_PATH`, se definido, tem prioridade. Antes da primeira execução nesse novo caminho, pare o servidor e copie o banco e a chave existentes para o diretório montado, mantendo os nomes access.sqlite3 e access.visitors.key. Só então reinicie. Não aponte para uma pasta vazia esperando que o histórico antigo apareça nela.

Mantenha uma única instância do servidor usando esse disco. Não distribua visitantes entre réplicas com bancos SQLite separados: isso produz totais diferentes. Para múltiplas réplicas, é necessário migrar o contador para um banco central compartilhado; este pacote não faz essa migração.

Configure a hospedagem para encaminhar /api/visit e /api/stats ao mesmo servidor, sem cache. As respostas já incluem Cache-Control: no-store. O cache do navegador é apenas visual, nunca a fonte do total. Preserve também os bancos e as chaves dos outros recursos conforme seus respectivos guias.

Números já apagados do banco só podem ser recuperados de um backup existente.
