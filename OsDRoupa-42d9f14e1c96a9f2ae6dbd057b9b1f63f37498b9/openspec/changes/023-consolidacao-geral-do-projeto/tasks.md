# Tarefas — 023-consolidacao-geral-do-projeto

## 0. Consolidação documental

- [x] Inventariar as 19 pastas OpenSpec não arquivadas anteriores a esta change.
- [x] Reunir as especificações e decisões técnicas preservando a divisão por domínio.
- [x] Trazer para esta lista as pendências que ainda podem ser executadas.
- [x] Declarar Xano como backend da entrega e SQLite como opção local.
- [x] Arquivar as pastas de origem após conferir todos os arquivos copiados.
- [x] Atualizar os índices OpenSpec e a documentação da estrutura.
- [ ] Mover os seis logs ainda bloqueados para `logs/` depois que as instâncias Reflex ativas encerrarem; 18 logs já foram movidos sem perda de conteúdo.
- [x] Confirmar que só esta change permanece ativa e que as 19 origens estão no arquivo.

## 1. Pendências por domínio

Os itens a seguir são as tarefas ainda abertas nas changes de origem. As listas completas, incluindo tarefas já concluídas, permanecem no arquivo histórico. Itens de Asaas da Change 008 foram substituídos pelo fluxo Mercado Pago da Change 020 e não devem ser reativados.

### Arquitetura da entrega Xano

- [ ] Inventariar as operações que ainda são atendidas apenas pelo backend SQLite e mapear cada uma para tabela, endpoint e regra Xano.
- [ ] Implementar os contratos Xano que faltam para autenticação, perfil, catálogo, endereços, armário/looks, pedidos, desafios/fidelidade e gestão.
- [ ] Aplicar e validar os schemas/endpoints no workspace Xano com perfis `member` e `admin`; manter SQLite apenas como modo local.
- [ ] Migrar ou desabilitar no Xano qualquer fluxo de cobrança Asaas e validar Mercado Pago antes de habilitar pagamento real.

### 003-address-and-cep

Fonte histórica: [`archive/003-address-and-cep/tasks.md`](../archive/003-address-and-cep/tasks.md).

- [ ] Exercitar CEP, múltiplos endereços, endereço padrão e isolamento entre duas contas.
- [ ] Confirmar o fluxo ponta a ponta com uma conta Xano de teste.

### 005-dashboard-retirement

Fonte histórica: [`archive/005-dashboard-retirement/tasks.md`](../archive/005-dashboard-retirement/tasks.md).

- [ ] Validar login e cadastro bem-sucedidos contra uma conta Xano de teste e observar o destino no navegador.

### 006-persistent-account-profile-wardrobe

Fonte histórica: [`archive/006-persistent-account-profile-wardrobe/tasks.md`](../archive/006-persistent-account-profile-wardrobe/tasks.md).

- [ ] Confirmar login, cookie, recarregamento e bloqueio de rotas com uma conta Xano de teste.
- [ ] Confirmar comportamento sem sessão, com JWT inválido e com indisponibilidade do Xano.
- [ ] Validar cadastro e perfil com dados reais no workspace Xano.

### 007-storefront-catalog

Fonte histórica: [`archive/007-storefront-catalog/tasks.md`](../archive/007-storefront-catalog/tasks.md).

- [ ] Cadastrar produtos de moda no Xano e validar respostas com dados reais; o catálogo atual contém alimentos e bebidas.
- [ ] Validar visualmente os estados de catálogo vazio, mal classificado e indisponível no navegador.
- [ ] Validar que resposta vazia ou falha da API não cria pedidos ou cobranças.

### 008-orders-checkout-payments

Fonte histórica: [`archive/008-orders-checkout-payments/tasks.md`](../archive/008-orders-checkout-payments/tasks.md).

Os itens de integração Asaas da fonte foram retirados do plano ativo porque a Change 020 adotou Mercado Pago. As tarefas abaixo desta seção são as pendências ainda válidas.

- [ ] Validar os estados visuais e formatos reais das respostas no navegador.
- [ ] Definir e validar liberação/expiração de estoque reservado após falha definitiva ou abandono do pagamento.
- [ ] Cadastrar produtos de moda no Xano antes de habilitar o checkout; o catálogo remoto atual contém itens fora do segmento.

### 009-wardrobe-cloud-sync

Fonte histórica: [`archive/009-wardrobe-cloud-sync/tasks.md`](../archive/009-wardrobe-cloud-sync/tasks.md).

- [ ] Exercitar isolamento entre contas, migração repetida e falhas de conexão no workspace Xano.

### 010-management-console

Fonte histórica: [`archive/010-management-console/tasks.md`](../archive/010-management-console/tasks.md).

- [ ] Implementar agregação financeira reconciliada e transições permitidas de status de pedido.
- [ ] Validar leitura, paginação, transições de status e acesso negado para `member`.
- [ ] Exercitar conta admin e member com Xano.

### 011-content-inspiration-challenges

Fonte histórica: [`archive/011-content-inspiration-challenges/tasks.md`](../archive/011-content-inspiration-challenges/tasks.md).

- [ ] Exercitar isolamento entre duas contas no workspace Xano.
- [ ] Exercitar rota privada e slug inválido no navegador.

### 012-smart-closet-iot

Fonte histórica: [`archive/012-smart-closet-iot/tasks.md`](../archive/012-smart-closet-iot/tasks.md).

- [ ] Validar navegação e estados com interação real no navegador.
- [ ] Implementar e publicar geração/consumo atômico de código de pareamento no Xano.
- [ ] Implementar confirmação de pareamento e ingestão de eventos com assinatura e idempotência.
- [ ] Validar propriedade entre duas contas, expiração/reuso, assinatura inválida e dispositivo offline no Xano.
- [ ] Validar o fluxo com hardware real.

### 013-outfits-calendar

Fonte histórica: [`archive/013-outfits-calendar/tasks.md`](../archive/013-outfits-calendar/tasks.md).

- [ ] Testar os contratos com duas contas no workspace Xano.
- [ ] Validar navegação, criação, remoção e estados vazios no navegador.
- [ ] Exercitar propriedade das peças, duplicidade, migração e isolamento entre duas contas no Xano.

### 014-ai-fashion-catalog-manual-checkout

Fonte histórica: [`archive/014-ai-fashion-catalog-manual-checkout/tasks.md`](../archive/014-ai-fashion-catalog-manual-checkout/tasks.md).

- [ ] Exercitar pedido autenticado com conta e endereço de teste no workspace.
- [ ] Gerar e publicar fotos dos produtos; a nova tentativa em 2026-10-23 retornou `429 credit_balance_exhausted` (`You have no credits remaining`). O catálogo continua usando ilustrações SVG locais até haver créditos disponíveis.

### 015-xano-rate-limit-resilience

Fonte histórica: [`archive/015-xano-rate-limit-resilience/tasks.md`](../archive/015-xano-rate-limit-resilience/tasks.md).

- [ ] Exercitar navegação autenticada e confirmar que o Xano não recebe chamadas duplicadas de sessão.

### 016-project-reliability-and-error-recovery

Fonte histórica: [`archive/016-project-reliability-and-error-recovery/tasks.md`](../archive/016-project-reliability-and-error-recovery/tasks.md).

- [ ] 2.1 Validar o XanoScript alterado em sandbox ou prévia de importação suportada.
- [ ] 2.2 Implementar e exercitar recuperação com envio SendGrid ao próprio usuário, resposta sem enumeração e uma conta de teste.
- [ ] 2.3 Exercitar sessão persistente, cookie de sessão, `429`, `403` de recurso e nova tentativa no navegador.
- [ ] 2.4 Publicar apenas depois de revisar uma prévia válida do workspace de destino.

### 020-armario-vivo-loyalty-mercadopago

Fonte histórica: [`archive/020-armario-vivo-loyalty-mercadopago/tasks.md`](../archive/020-armario-vivo-loyalty-mercadopago/tasks.md).

- [ ] Revisar os novos fluxos e confirmar configuração de credenciais/sandbox antes de habilitar cobranças reais.

### 021-experiencia-cliente-completa

Fonte histórica: [`archive/021-experiencia-cliente-completa/tasks.md`](../archive/021-experiencia-cliente-completa/tasks.md).

- [ ] Verificar compilação Reflex e revisar manualmente as páginas em tamanhos móvel e desktop.
- [ ] Importar, validar e publicar os contratos XanoScript apenas quando o modo Xano for adotado.
- [ ] Exercitar o Mercado Pago em sandbox com credenciais e webhook HTTPS do operador.

### 022-boutiques-ficticias-catalogo-moda

Fonte histórica: [`archive/022-boutiques-ficticias-catalogo-moda/tasks.md`](../archive/022-boutiques-ficticias-catalogo-moda/tasks.md).

- [ ] Aplicar o schema, endpoints e seed ao workspace Xano da apresentação.
- [ ] Confirmar no workspace Xano a leitura pública e o cadastro com conta administrativa.
- [ ] Compilar o app e revisar a loja em celular e desktop.
- [ ] Confirmar a persistência em um banco existente por inspeção manual.

## 2. Fechamento da consolidação

- [x] Consolidar o escopo e a ordem dos módulos conforme a solicitação do projeto.
- [ ] Arquivar esta change somente depois de concluir ou replanejar explicitamente as tarefas pendentes e atualizar as specs canônicas.
