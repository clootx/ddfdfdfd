# Tarefas — 012-smart-closet-iot

## Status: UI LOCAL CONCLUÍDA; INTEGRAÇÃO XANO/HARDWARE PENDENTE

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.

### Produto e UX
- [x] Criar lista, pareamento e detalhe de dispositivo.
- [x] Diferenciar dispositivo ausente, pareamento pendente, conectado e sem contato.
- [ ] Validar navegação e estados com interação real no navegador.

### Backend e hardware
- [x] Criar rascunhos locais das tabelas de dispositivo, pareamento e evento.
- [x] Criar rascunhos locais de leitura privada da lista e do detalhe por conta autenticada.
- [ ] Implementar e publicar geração/consumo atômico de código de pareamento no Xano.
- [ ] Implementar confirmação de pareamento e ingestão de eventos com assinatura e idempotência.
- [ ] Validar propriedade entre duas contas, expiração/reuso, assinatura inválida e dispositivo offline no Xano.
- [ ] Validar o fluxo com hardware real.

### Verificação
- [x] Compilar e gerar build Reflex.
- [x] Validar sintaxe Xano dos schemas e leituras privadas locais.
- [x] Validar HTTP das rotas `/dispositivos`, `/dispositivos/conectar` e `/dispositivo?id=1`.
- [x] Validar handshake WebSocket Engine.IO do Reflex.
- [ ] Validar os rascunhos no workspace Xano antes de importar ou publicar.
