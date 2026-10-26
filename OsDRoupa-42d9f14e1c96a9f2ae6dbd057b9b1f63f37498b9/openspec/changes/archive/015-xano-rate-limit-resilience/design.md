# Design — 015-xano-rate-limit-resilience

## Limitador de chamadas

Um cliente HTTP Reflex comum controla as chamadas dirigidas ao domínio Xano. Uma janela móvel grava os horários e o cooldown em tabelas SQLite transacionais, compartilhadas entre os workers locais que usam o mesmo caminho de banco, para iniciar até oito requisições em 20 segundos. As chamadas para serviços externos, como ViaCEP, não consomem essa cota local. Instalações em múltiplas máquinas ainda precisam de um coordenador compartilhado como Redis.

Se o Xano retornar 429, o cliente persiste uma pausa de 20 segundos antes de iniciar novas chamadas. A chamada que recebeu 429 não é repetida automaticamente: isso evita duplicar pedidos e outras operações com efeito colateral. O limitador coordena workers locais pelo mesmo arquivo SQLite; outro app ou workspace ainda pode consumir a margem restante, e instalações em máquinas diferentes precisam de um coordenador compartilhado.

## Sessão

Após `/auth/me` confirmar o token e `buscaCliente` preencher o perfil, o estado Reflex reutiliza essa validação por 60 segundos. Login, cadastro, logout e respostas 401/403 limpam a validação. Cada endpoint privado continua recebendo o Bearer token e mantém a autorização no Xano.

## Catálogo

Somente a resposta pública e normalizada do catálogo é mantida em memória por 60 segundos, compartilhada entre estados do mesmo processo. Cada estado recebe uma cópia dos dados para que sincronização de preços e sacola não altere o cache. Dados privados e pedidos não são armazenados nesse cache.

## Interface e falhas

Loja e detalhe do produto explicam que o catálogo atingiu o limite temporário e orientam a aguardar até 20 segundos. Erros de rede permanecem distinguíveis de 429. A aplicação não informa que a cota está garantida, pois o Xano compartilha o limite com outros consumidores da instância.

## WebSocket

O canal `/_event` em `localhost:8001` é o transporte Socket.IO/Engine.IO usado pelo Reflex para eventos entre o navegador e o estado Python. O handshake funciona pelo protocolo Engine.IO (`EIO=4&transport=websocket`); um handshake WebSocket cru retorna 403 por não iniciar esse protocolo.

O Xano Realtime V2 é outro serviço: usa servidores, canais e handlers de mensagem próprios. A aplicação não tem polling periódico do Xano para substituir por eventos. Não há garantia documentada de que chamadas de handlers Realtime fiquem fora da cota do plano gratuito, então o canal não será usado para contornar o limite REST. O tratamento permanece no enfileiramento, cache e pausa após 429.
