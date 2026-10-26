# Tarefas — 015-xano-rate-limit-resilience

## Implementação

- [x] Registrar proposta, design, requisitos e cenários de aceite.
- [x] Criar cliente HTTP comum que limita chamadas ao Xano a 8 por 20 segundos, compartilhado entre workers que usam o mesmo SQLite.
- [x] Pausar chamadas seguintes por 20 segundos após uma resposta 429, sem retentar escritas.
- [x] Reutilizar sessão validada e cachear catálogo público por 60 segundos.
- [x] Mostrar orientação de espera para 429 no catálogo e detalhe do produto.
- [x] Compilar o Reflex e confirmar resposta HTTP 200 na rota inicial.
- [x] Verificar o handshake Engine.IO do WebSocket do Reflex e confirmar que o app não faz polling periódico do Xano.
- [ ] Exercitar navegação autenticada e confirmar que o Xano não recebe chamadas duplicadas de sessão.
- [x] Coordenar a janela e o cooldown de chamadas entre processos locais usando transações SQLite.
