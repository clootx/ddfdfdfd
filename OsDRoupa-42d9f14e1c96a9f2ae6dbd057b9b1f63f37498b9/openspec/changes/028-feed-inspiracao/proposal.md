# Proposta — 028-feed-inspiracao

## Contexto

`/inspiracao` mostra três ideias fixas (`INSPIRATION_IDEAS`, RF-CONT-01). As propostas da IA (Changes 025 a 027), com avaliação e imagem gerada, somem quando a página é recarregada; só as peças do armário podem ir para "Meus Looks". Não existe feed, nem forma de salvar ou descobrir combinações de outras pessoas. A Change 013 deixou o feed social fora do escopo.

## Objetivo

Persistir os looks da IA como inspirações e criar um feed de descoberta com filtros, salvamento e publicação anônima moderada, sem expor fotos privadas do armário.

## Escopo incluído

- "Guardar inspiração" nos cards da IA: salva nome, ocasião, clima, região, estação, paleta, tecidos, justificativa, nota da avaliação, peças e imagem gerada.
- `/inspiracao` com abas **Descobrir** (feed público com filtros de ocasião, clima e região, paginação de 24) e **Minhas inspirações** (criadas, com status, e salvas do feed). As ideias editoriais fixas continuam na página.
- Salvar e remover dos salvos looks publicados.
- "Enviar ao feed" com consentimento explícito de publicação anônima. A inspiração vai para revisão (`Pendente`) e só aparece no feed depois de aprovada em `/gestao/inspiracoes`.
- Backend SQLite completo e rascunhos Xano (2 tabelas e 9 endpoints) no padrão dos rascunhos existentes.

## Escopo excluído

- Publicações livres de usuários (fotos próprias, textos), curtidas, comentários e seguidores (Change 029, opcional).
- Feed personalizado por recomendação.
- Publicar no Xano: os rascunhos precisam ser importados e validados no workspace (pendência já registrada na 023 para os demais contratos).

## Dependências e impactos

- **Modelagem de dados:** novas tabelas `inspirations`/`LOOK_INSPIRACAO` e `inspiration_saves`/`INSPIRACAO_SALVA`.
- **APIs:** `GET feedInspiracoes` (pública), `GET/POST minhasInspiracoes`, `DELETE minhasInspiracoes/{id}`, `POST publicarInspiracao/{id}`, `POST/DELETE inspiracoesSalvas/{id}`, `GET adminInspiracoes`, `PATCH adminInspiracoes/{id}`.
- **Frontend:** novo `InspirationState`; `/inspiracao`; nova página `/gestao/inspiracoes` e item no menu de gestão; botão nos cards da IA.
- **Depende de:** 025 (propostas); 026 e 027 enriquecem as inspirações com nota e imagem.
