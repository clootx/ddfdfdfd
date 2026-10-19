# Design — 011-content-inspiration-challenges

## Rotas e dados

| Rota | Acesso | Dados |
|---|---|---|
| `/inspiracao` | Público | Ideias curadas locais com links para loja e armário |
| `/artigos` | Público | Lista editorial versionada no Python |
| `/artigo?id={slug}` | Público | Detalhe da mesma coleção editorial |
| `/desafios` | Conta autenticada | Desafios próprios e progresso local por ID da conta |

## Progresso pessoal

`ContentState` valida o JWT antes de ler ou alterar desafios. O `localStorage` guarda mapa por ID de usuário; cada desafio pode ser concluído uma vez. A UI informa que o progresso ainda não sincroniza com o Xano. Não há placar público nem pontuação competitiva nesta etapa.

## Conteúdo

Artigos e ideias são conteúdo editorial estático do repositório, não feed de usuários. A busca e as páginas de detalhe usam slugs estáveis. Conteúdo remoto e edição por CMS ficam para uma change posterior.

## Verificação

Compilar Reflex, gerar build e validar rotas. Confirmar guard de `/desafios`, isolamento local entre contas e estado sem artigos/desafios após alteração da coleção.
