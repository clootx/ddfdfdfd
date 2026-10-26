# Proposta Arquivada — 001-foundation-identity-client

> **Status:** Arquivada (Concluída em 14/09/2026 - 28/09/2026)  
> **Especificações Promovidas:** [`openspec/specs/auth/spec.md`](../../../specs/auth/spec.md) e [`openspec/specs/cliente/spec.md`](../../../specs/cliente/spec.md)

## Contexto
O sistema apresentava a necessidade de uma fundação sólida de identidade e cadastro de clientes para conectar o backend Xano ao frontend Reflex, permitindo autenticação segura e criação de perfis vinculados a contas e status válidos.

## Objetivo
Estabelecer a base mínima de autenticação e cadastro do cliente:
- Autenticação do usuário no sistema com e-mail e senha.
- Vínculo seguro entre usuário e cliente (`user_id`).
- Criação e consulta do perfil do cliente.
- Base consistente para os próximos fluxos de endereço, catálogo e pedidos.

## Escopo Entregue
- Cadastro de usuário com validação de e-mail e requisitos de senha.
- Login com retorno de token JWT e sessão.
- Criação de cliente via endpoint `cadastraCliente` no grupo `PANELA_DE_BARRO`.
- Associação com `STATUS_CLIENTE` inicial e `user_id`.
- Interface inicial no Reflex com `AuthState` e alternância de tabs Login/Cadastro.

## Escopo Excluído
- Endereços e CEP (delegado para Change 002).
- Catálogo de produtos, pedidos, produção e pagamentos (delegados para changes posteriores).
