# Design — 011-content-inspiration-challenges

## Rotas e dados

| Rota | Acesso | Dados |
|---|---|---|
| `/inspiracao` | Público | Ideias curadas locais com links para loja e armário |
| `/artigos` | Público | Lista editorial versionada no Python |
| `/artigo?id={slug}` | Público | Detalhe da mesma coleção editorial |
| `/desafios` | Conta autenticada | Desafios próprios e progresso local por ID da conta |

## Progresso pessoal

`ContentState` valida o JWT antes de ler ou alterar desafios. `DESAFIO_CONCLUIDO` guarda uma conclusão por usuário e slug, com índice único composto. O `localStorage` mantém uma cópia por ID de usuário para uso sem conexão; a interface distingue progresso sincronizado de progresso local. Não há placar público nem pontuação competitiva nesta etapa.

Os endpoints autenticados `GET /meusDesafios` e `POST /concluirDesafio` só consultam ou gravam o ID da sessão atual. O endpoint de conclusão valida os quatro slugs publicados no aplicativo e é idempotente para repetições do mesmo usuário.

## Direção visual

As telas combinam conteúdo editorial limpo e fácil de percorrer com progresso pessoal e desafios leves. Cartões usam realce discreto ao passar o cursor; a barra de progresso comunica avanço sem transformar o recurso em competição pública. Transições respeitam `prefers-reduced-motion`.

## Conteúdo

Artigos e ideias são conteúdo editorial estático do repositório, não feed de usuários. A busca e as páginas de detalhe usam slugs estáveis. Conteúdo remoto e edição por CMS ficam para uma change posterior.

## Verificação

Compilar Reflex, gerar build e validar rotas. Confirmar guard de `/desafios`, isolamento local entre contas e estado sem artigos/desafios após alteração da coleção.
