# Change 015 — Resiliência ao limite de chamadas do Xano

## Problema

A instância gratuita do Xano limita chamadas a 10 por janela de 20 segundos. A aplicação repetia a validação de sessão em cada navegação e recarregava o catálogo ao abrir a loja e a sacola, provocando respostas HTTP 429 durante o uso rápido.

## Objetivo

Reduzir chamadas redundantes e enfileirar as chamadas do Reflex dentro de uma margem compatível com o limite da instância, com uma mensagem clara quando o próprio Xano ainda responder 429.

## Escopo

- Controlar chamadas do Reflex ao Xano entre workers locais que compartilham o mesmo SQLite, com no máximo 8 por janela móvel de 20 segundos.
- Reutilizar a sessão já validada no estado Reflex por 60 segundos, além de limpá-la na troca ou invalidação do token.
- Reutilizar o catálogo público por 60 segundos.
- Aplicar uma pausa de 20 segundos depois de um 429 e evitar novas tentativas automáticas de operações de escrita.
- Informar a espera na loja e no detalhe do produto.

## Fora do escopo

- Alterar limites do plano Xano ou contratar um plano pago.
- Retentar automaticamente pedidos, pagamentos ou outras escritas.
- Cachear dados privados entre contas.

## Critérios de aceite

- Navegar entre páginas autenticadas não repete `/auth/me` e `buscaCliente` enquanto a sessão Reflex continuar validada.
- Loja e sacola reutilizam a resposta pública do catálogo durante 60 segundos.
- Todas as chamadas da aplicação ao domínio Xano passam pelo limitador compartilhado entre os workers locais.
- Um 429 pausa chamadas seguintes e apresenta orientação de espera sem repetir uma escrita.
