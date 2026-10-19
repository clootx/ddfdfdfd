# Design Técnico Arquivado — 001-foundation-identity-client

## Arquitetura Implementada

A autenticação e cadastro de clientes combinam o frontend Reflex com os grupos de API do Xano:

```text
Reflex (AuthState) ──► Xano API (/auth/signup, /auth/login, cadastraCliente) ──► PostgreSQL (user, CLIENTE)
```

## Endpoints e Funções Consolidadas

1. `POST /api:auth/signup`: Criação de usuário em `user`.
2. `POST /api:auth/login`: Autenticação e geração de `authToken`.
3. `GET /api:auth/me`: Verificação do token e dados do usuário atual.
4. `POST /api:PANELA_DE_BARRO/cadastra_cliente`: Criação atômica de usuário + cliente + vínculo com `user_id`.

## Modelo de Dados Consolidado
- Tabela `user`: `id`, `name`, `email`, `password`, `account_id`, `created_at`.
- Tabela `CLIENTE`: `id`, `nome`, `celular`, `cpf`, `status_cliente_id`, `user_id`, `created_at`.
- Tabela `STATUS_CLIENTE`: `id`, `status_cliente`.
