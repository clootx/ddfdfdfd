# Design: backend local persistente

## Decisão

Usar SQLite acessado pelo backend Python do Reflex. A implementação preserva a camada de chamadas já usada pela interface: quando `OSDROUPA_BACKEND=sqlite`, o cliente interno encaminha apenas URLs Xano para um adaptador local compatível com os contratos existentes. `OSDROUPA_BACKEND=xano` mantém chamadas remotas. SQLite é apropriado para desenvolvimento local e uma única instância; produção multi-instância deve usar PostgreSQL ou serviço equivalente.

## Persistência e segurança

- Um arquivo SQLite fora do versionamento, definido por `OSDROUPA_DB_PATH`.
- Conexões curtas por operação, transações, chaves estrangeiras, WAL e consultas parametrizadas.
- Senhas derivadas com PBKDF2-HMAC-SHA256 e salt aleatório; sessões armazenam apenas hash do token, expiração e usuário.
- Todo endpoint privado resolve usuário pelo Bearer token no servidor; filtros por usuário são aplicados também em endereços, peças, looks, desafios e pedidos.
- Papel administrativo é concedido somente ao e-mail definido por `OSDROUPA_ADMIN_EMAIL`; o cliente não escolhe o próprio papel.
- A recuperação de senha cria token de uso único. Com SMTP, envia por e-mail; sem SMTP no modo SQLite local, oferece um link local explicitamente identificado e nunca diz que enviou e-mail. `OSDROUPA_LOCAL_RECOVERY=0` desativa o fallback local.
- Checkout local cria pedido demonstrativo pendente, reserva estoque temporariamente e nunca cria cobrança ou marca pagamento como aprovado.
- Pareamento local é identificado como demonstração e não representa vínculo com hardware real.

## Entidades

`users`, `sessions`, `addresses`, `products`, `wardrobe_items`, `looks`, `challenge_completions`, `orders`, `order_items`, `device_pairings` e `password_reset_tokens`.

## Contratos usados pela interface

O adaptador responde aos contratos existentes para autenticação, cliente, endereços, armário, looks, produto, checkout demonstrativo, pedidos, desafios, pareamento e leitura administrativa. Novas operações administrativas de produto/status ficam sob endpoints locais protegidos por papel `admin`.

## Interface

- O perfil ganha formulário de edição.
- A gestão ganha cadastro de produto e ações de transição válidas para pedidos.
- A recuperação de senha passa a ter rotas de solicitação e redefinição; sem SMTP local, exibe um link de uso único na própria tela.
- A interface identifica checkout e pareamento locais como demonstração.

## Migração e operação

Não há importação automática dos registros Xano nem compartilhamento do arquivo SQLite entre dispositivos. O operador pode preservar Xano definindo `OSDROUPA_BACKEND=xano`. A criação de schema/seed ocorre de forma idempotente no primeiro acesso local.
