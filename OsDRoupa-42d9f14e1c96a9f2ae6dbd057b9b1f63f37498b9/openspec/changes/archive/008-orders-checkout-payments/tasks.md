# Tarefas — 008-orders-checkout-payments

## Status: IMPLEMENTAÇÃO PUBLICADA; CONFIGURAÇÃO E ATIVAÇÃO PENDENTES

> O backend SQLite da Change 017 implementa pedido demonstrativo idempotente, estoque reservado e histórico, sem efetuar cobrança. As tarefas Asaas abaixo são exclusivas do modo Xano.

### OpenSpec
- [x] Registrar proposta, design, requisitos e cenários.
- [x] Registrar a change no índice.
- [x] Limitar a primeira forma de pagamento a PIX conforme os estados existentes.

### Backend Xano local
- [x] Adicionar endereço e chave de idempotência a PEDIDO e vínculo TRANSACAO.pedido_id.
- [x] Restringir rotas CRUD genéricas de pedido, item, transação e cliente a administradores.
- [x] Desativar rotas Asaas legadas com valor livre ou token de autenticação na entrada.
- [x] Criar consulta privada de histórico e detalhe, checkout com validação de propriedade, preço/categoria/estoque e total recalculado.
- [x] Implementar chave idempotente e recuperação de cobrança pelo externalReference antes de criar uma nova cobrança PIX.
- [x] Criar webhook com segredo separado, deduplicação por evento e confirmação apenas após PAYMENT_RECEIVED.
- [x] Validar a sintaxe local dos schemas e endpoints com o parser oficial Xano.
- [x] Publicar fontes e schema no workspace Xano, branch live `v1` (workspace `147975`).
- [ ] Configurar segredos Asaas e validar o fluxo com duas contas no sandbox.

### Frontend Reflex
- [x] Criar /checkout, /pedidos e /pedido?id={id}.
- [x] Enviar somente IDs/quantidades e preservar a chave em falha de rede.
- [x] Incluir endereço e itens na chave de idempotência.
- [x] Exibir instrução PIX só após resposta válida e mostrar estado da cobrança nos pedidos.
- [ ] Validar os estados visuais e formatos reais das respostas no navegador.

### Verificação e ativação
- [x] Executar py_compile, compilação Reflex e build de produção; confirmar respostas HTTP das rotas locais.
- [x] Validar sintaxe Xano dos schemas e endpoints locais alterados.
- [ ] Exercitar propriedade do endereço, estoque, idempotência, isolamento e erros Asaas no sandbox.
- [ ] Definir e validar liberação/expiração de estoque reservado após falha definitiva ou abandono do pagamento.
- [x] Auditar no XanoScript que o total é recalculado com preço do Xano e o pagamento só é confirmado após webhook autenticado, com valor e referência conferidos.
- [ ] Cadastrar produtos de moda no Xano antes de habilitar o checkout; o catálogo remoto atual contém itens fora do segmento.
