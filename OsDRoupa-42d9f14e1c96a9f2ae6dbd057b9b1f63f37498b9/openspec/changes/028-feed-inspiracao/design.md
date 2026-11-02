# Design Técnico — 028-feed-inspiracao

## Visão Geral da Arquitetura

```text
card da IA ─► WardrobeLifeState.save_ai_inspiration ─► POST minhasInspiracoes
/inspiracao ─► InspirationState (load_inspiration_page)
                 ├─ GET feedInspiracoes?ocasiao&clima&regiao&pagina   (público)
                 ├─ GET minhasInspiracoes  → {criadas, salvas}
                 ├─ POST/DELETE inspiracoesSalvas/{id}
                 ├─ POST publicarInspiracao/{id} {autorizo_publicacao: true}
                 └─ DELETE minhasInspiracoes/{id}
/gestao/inspiracoes ─► GET adminInspiracoes · PATCH adminInspiracoes/{id} {status}
```

Mesma base `XANO_PDB` dos demais recursos pessoais. No modo SQLite, o `XanoAsyncClient` encaminha as chamadas para `professormateria/local_backend.py` (`_inspiration_routes`).

## Modelo de dados

| SQLite `inspirations` / Xano `LOOK_INSPIRACAO` | Observação |
|---|---|
| `user_id` / `cliente_id` | Dono; nunca devolvido no feed |
| `local_key` / `chave_local` (único) | `proposal.id` (hex de 32), garante idempotência |
| `name`, `occasion`, `weather_category`, `region`, `season` | Filtros validados contra listas fechadas |
| `palette`, `fabrics`, `rationale`, `score` | Textos limitados (200/200/1200/4) |
| `pieces_json` / `pecas` | Até 12 peças; `imagem_url` só para origem `catalogo` |
| `image_path` / `imagem` | `looks/<hex32>.(png\|jpg\|webp)` ou vazio |
| `status` | `Privado` → `Pendente` → `Publicado`/`Recusado` (`Recusado` → `Pendente` de novo) |

`inspiration_saves` / `INSPIRACAO_SALVA`: chave única (dono, inspiração); `ON DELETE CASCADE` no SQLite e remoção explícita no rascunho Xano.

## Contratos

- `GET feedInspiracoes` → `{inspiracoes: [...], pagina, tem_mais}`; cada item tem `id, nome, ocasiao, clima, regiao, estacao, paleta, tecidos, justificativa, nota, pecas, imagem, autor: "Pessoa da comunidade", data`.
- `GET minhasInspiracoes` → `{criadas: [... + status, chave_local], salvas: [... + salvo: true]}`.
- `POST minhasInspiracoes` → 201 `{inspiracao}` (200 se a chave já existe para a mesma conta; 403 se é de outra conta; 400 em validação).
- `POST publicarInspiracao/{id}` → 400 sem consentimento; 404 se não é dono ou se o status não permite.
- `PATCH adminInspiracoes/{id}` → só `Publicado`/`Recusado`; 403 sem papel admin.

## Estado e UI (Reflex)

- Dataclasses `Inspiration` e `InspirationPiece` para `rx.foreach` tipado; `capa_catalogo` é a primeira imagem de catálogo, usada quando não há imagem gerada.
- `InspirationState(AuthState)`: `feed`, `my_created`, `my_saved`, `admin_inspirations`, filtros, paginação, `feed_tab` e `publish_candidate_id` (confirmação de consentimento em linha).
- Componentes: `inspiration_cover`, `inspiration_feed_card` (variações público/dona/admin), `inspiration_feed_section` (abas, filtros, carregar mais), `admin_inspirations_page`.

## Decisões

1. **Fotos do armário nunca saem do perfil:** o cliente já remove essas fotos, e o servidor repete a regra (SQLite descarta; o rascunho Xano recusa `data:`). A imagem gerada pode refletir as peças, por isso o texto de consentimento diz isso.
2. **Moderação antes de publicar:** segue o padrão dos depoimentos. Imagens geradas por IA e textos ficam públicos, e o filtro de segurança do provedor não substitui a revisão humana.
3. **Anonimato:** o feed nunca devolve dono, status interno nem chave.
4. **Imagem no servidor Reflex:** `imagem` guarda o caminho relativo servido pelo diretório de uploads do Reflex. Em produção com várias instâncias, esse diretório precisa ser um volume compartilhado ou um armazenamento de objetos (pendência).
5. **Endpoint `publicarInspiracao/{id}`:** em vez de `minhasInspiracoes/{id}/publicar`, porque o roteador local identifica o recurso pelo último segmento numérico.
