# Proposta Arquivada — 018-responsive-storytelling-pages

> **Status:** Concluída e arquivada em 23/10/2026  
> **Especificação promovida:** [`openspec/specs/institutional-pages/spec.md`](../../../specs/institutional-pages/spec.md)

## Problema

A navegação institucional da home usa âncoras que apontam para blocos genéricos ou inexistentes. Em telas pequenas, os links principais desaparecem e o cabeçalho pode ultrapassar a largura disponível. A home também apresenta informações promocionais sem fonte e não conduz a pessoa por uma narrativa de rolagem.

## Objetivo

Entregar páginas próprias de serviços e alfaiataria, depoimentos e como funciona; corrigir a navegação responsiva do site; e dar à home uma progressão visual fluida, acessível e coerente com a identidade do OSDROUPA.

## Escopo

- Criar as rotas `/servicos`, `/depoimentos` e `/como-funciona` com navegação consistente.
- Adaptar a navegação institucional e da loja para telas pequenas e largas.
- Aplicar animações de entrada ligadas à rolagem, indicador de progresso e rolagem suave na narrativa institucional.
- Respeitar `prefers-reduced-motion` e manter conteúdo legível em navegadores sem suporte às animações guiadas por rolagem.
- Revisar as mensagens da home para corresponder aos fluxos existentes e não apresentar estatísticas ou avaliações inventadas.
- Validar as páginas e o overflow horizontal em viewports móveis, tablet e desktop.

## Fora do escopo

- Copiar identidade, conteúdo, imagens ou animações proprietárias do SquadEasy.
- Inventar depoimentos de clientes ou afirmar integrações ainda não disponíveis.
- Criar agendamento, atendimento ou integração de pagamento para serviços de alfaiataria.
- Alterar o backend ou publicar mudanças externas.

## Critérios de aceite

- Os links institucionais abrem as rotas correspondentes e também ficam acessíveis em telas estreitas.
- Nenhuma página revisada cria rolagem horizontal involuntária em 320, 390, 768 e 1280 px.
- A home revela suas seções ao descer, mostra o progresso da página e permite seguir para o passo a passo.
- Animações são desligadas quando o dispositivo pede movimento reduzido.
- A página de depoimentos não apresenta avaliações fictícias como experiências reais.
