# Tarefas — 012-smart-closet-iot

## Status: UI E LEITURAS PUBLICADAS; PAREAMENTO E HARDWARE PENDENTES

> No SQLite, pareamento é uma demonstração local sem hardware ou ingestão real de eventos. As tarefas de assinatura, publicação e dispositivo físico continuam fora dessa demonstração.

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Produto e UX
- [x] Criar lista, pareamento e detalhe de dispositivo.
- [x] Diferenciar dispositivo ausente, pareamento pendente, conectado e sem contato.
- [x] Mostrar último contato na lista e aplicar microinterações responsivas com suporte a movimento reduzido.
- [ ] Validar navegação e estados com interação real no navegador.

### Backend e hardware
- [x] Criar e publicar as tabelas de dispositivo, pareamento e evento no workspace Xano.
- [x] Criar e publicar leituras privadas da lista e do detalhe, filtradas pela conta autenticada.
- [ ] Implementar e publicar geração/consumo atômico de código de pareamento no Xano.
- [ ] Implementar confirmação de pareamento e ingestão de eventos com assinatura e idempotência.
- [ ] Validar propriedade entre duas contas, expiração/reuso, assinatura inválida e dispositivo offline no Xano.
- [ ] Validar o fluxo com hardware real.

### Verificação
- [x] Compilar e gerar build Reflex.
- [x] Validar sintaxe Xano dos schemas e leituras privadas locais.
- [x] Validar HTTP das rotas `/dispositivos`, `/dispositivos/conectar` e `/dispositivo?id=1`.
- [x] Validar handshake WebSocket Engine.IO do Reflex.
- [x] Confirmar que os cinco scripts publicados estão sincronizados com a branch live `v1` (workspace `147975`); prévia em 2026-10-22 sem diferenças pendentes.
