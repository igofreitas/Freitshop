> A página consulta os totais a cada 5 segundos sem contar novamente. Consulte CONTADOR-PERSISTENTE.md para configurar armazenamento durável.

# Contador por navegador

O app registra a visita em POST /api/visit e recebe os totais atualizados. GET /api/stats apenas consulta. Isso funciona mesmo quando o HTML vem de cache, desde que /api/* chegue ao servidor Python na mesma origem.

Cada navegador recebe um cookie aleatório assinado, HttpOnly, SameSite=Lax, válido por um ano; em HTTPS configurado, Secure. A mesma identificação conta uma vez por dia (UTC−3). Dois navegadores ou aparelhos na mesma rede contam separadamente. Atualizar a página não aumenta o contador no mesmo dia. Apagar/bloquear cookies, modo privado ou outro navegador pode gerar nova visita. Não é possível distinguir duas pessoas no mesmo perfil de navegador sem login.

O banco salva um HMAC diário, não o cookie ou IP bruto. As chaves e o banco ficam na pasta data; mantenha essa pasta em disco persistente. STATS_DB_PATH, VISITOR_KEY_FILE e VISITOR_HASH_KEY permitem configuração personalizada. Preserve a chave entre reinícios. Os totais anteriores são preservados; antes desta atualização foram medidos por IP e não podem ser recalculados retroativamente. No dia da atualização, um visitante antigo poderá contar novamente com seu novo identificador.

TRUSTED_PROXY_HOPS é usado apenas para o limite antispam do feedback. Deixe 0 na execução direta; configure o número exato de proxies confiáveis apenas se a infraestrutura exigir.
