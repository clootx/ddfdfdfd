# Change 004 — Integração de Autenticação com Xano

## Contexto

A Change 002 entregou a página de autenticação completa com validações locais robustas. Contudo, os handlers `handle_login` e `handle_register` apenas simulam o fluxo — não há chamadas reais à API do Xano, não há persistência de token e não há redirecionamento para o painel após o login bem-sucedido.

Esta change fecha esse ciclo conectando o frontend Reflex aos endpoints reais do Xano, armazenando o `authToken` JWT no estado da aplicação e redirecionando o usuário autenticado para a página inicial do sistema (`/dashboard`).

## Objetivo

- Substituir a validação simulada por chamadas HTTP reais ao Xano
- Armazenar o JWT retornado no `AuthState`
- Redirecionar para `/dashboard` após login ou cadastro bem-sucedidos
- Exibir erros reais do Xano inline nos formulários
- Criar a página `/dashboard` como destino pós-autenticação

## Endpoints Consumidos

| Endpoint | Método | Grupo |
|---|---|---|
| `/api:nqm5-KuC/auth/login` | POST | Authentication |
| `/api:6LtoY7Zt/cadastraCliente` | POST | PANELA_DE_BARRO |
| `/api:nqm5-KuC/auth/me` | GET | Authentication (Bearer) |

## Base URL Xano

`https://x8ki-letl-twmt.n7.xano.io`

## Critérios de Aceite

- [x] Login com credenciais válidas → redireciona para `/dashboard`
- [x] Login com credenciais inválidas → exibe "Invalid Credentials." inline
- [x] Cadastro com e-mail já existente → exibe "This account is already in use." inline
- [x] Cadastro bem-sucedido → redireciona para `/dashboard`
- [x] `authToken` JWT disponível no estado para rotas protegidas
- [x] Página `/dashboard` protegida: sem token → redireciona para `/`
- [x] Estado de carregamento (`is_loading`) desativa o botão durante a requisição

## Dependências

- `httpx==0.28.1` (já instalado via venv do projeto)
- Change 002 (página de auth) — pré-requisito concluído
