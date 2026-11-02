# Tarefas — 029-estilista-gemini

## Status: ETAPAS 3 A 6 IMPLEMENTADAS (PROVEDOR, LIMITES, PLANO B, LOOKS MAIS RICOS); CHAMADA REAL PENDENTE

### OpenSpec
- [x] Registrar proposta, requisitos, design e tarefas.
- [x] Anotar nas Changes 025, 026 e 027 o que foi substituído.
- [x] Atualizar o índice.

### Provedor (Etapa 3)
- [x] `OSDroupa/ai/providers/__init__.py`: `TextProvider`, `ProviderError`, `get_text_provider`.
- [x] `OSDroupa/ai/providers/gemini.py`: Interactions API, `GEMINI_API_KEY`, `GEMINI_MODEL` (padrão `gemini-3.8-flash`), mapeamento de erros e log sem segredos.
- [x] `stylist.py` sem SDK; nova tentativa só para resposta fora do formato.
- [x] Remover `anthropic` do `requirements.txt`, do código, do `.env.example` e dos textos da interface.
- [x] `OSDROUPA_IMAGES_ENABLED=false` por padrão em `imaging.py`.
- [x] Política de privacidade: dados enviados ao Google e aviso do plano gratuito.
- [x] Testes (MOCK): provedor falso no estilista; Interactions API falsa no provedor (parâmetros, 429/401/403/404/400/503, status `failed`, saída vazia, chave fora dos logs, fábrica); trava de imagem (a chave sozinha não liga).
- [x] `pytest` 101 passed, `pyflakes` sem avisos, `reflex compile` OK, bundle sem chave nem prompt, projeto roda sem o pacote `anthropic`.

### Limites persistentes (Etapa 4)
- [x] `LocalBackend.reserve_rate_limit_slots`: reserva atômica em vários baldes (tudo ou nada), nas mesmas tabelas `outbound_rate_limits`; o método antigo não mudou.
- [x] `OSDroupa/ai/limits.py`: por conta/hora, global/minuto e global/dia, separados para texto e imagem, configuráveis por ambiente; mensagens distintas para conta, plataforma e pausa.
- [x] Pausa global ao receber 429 (texto ou imagem), em balde próprio, por `OSDROUPA_AI_QUOTA_PAUSE_SECONDS`.
- [x] Remover o limitador em memória (`stylist.reserve_generation`, `imaging.images_per_hour`).
- [x] Testes: atomicidade (vaga não consumida na recusa), conta, minuto, dia, texto × imagem separados, sobrevivência a reinício, pausa para todas as contas, pausa sem consumo, conta ausente, tipo inválido. `pytest` 111 passed.

### Plano B do Look do Dia no modo Xano (Etapa 5)
- [x] `OSDroupa/daily_look.py`: mesma regra do `lookDoDia` SQLite, em Python, sem chamadas externas.
- [x] `load_daily_look` usa o plano B só quando o endpoint falha; registra o erro real no log e mostra o motivo ("Sugestão calculada localmente porque…").
- [x] Testes: paridade com o endpoint SQLite em 16 combinações de clima × ocasião, regras (suja/lavando, 4 peças, 1 por categoria) e motivos curtos sem URL. `pytest` 135 passed.
- [x] Rascunho `xano/api/panela_de_barro/look_do_dia_GET.xs` (mesma regra).
- [ ] **Depende do workspace Xano:** importar, validar filtros (`to_lower`, `contains`, `in`), testar e publicar o `lookDoDia` e os 11 rascunhos da Change 028.
- [ ] Outros 14 endpoints usados pelo app continuam só no SQLite (depoimentos, fidelidade, malas, uso, privacidade, alfaiataria, pareamento); no modo Xano essas telas mostram erro até serem publicados.

### Looks mais ricos (Etapa 6)
- [x] Schema: `descricao` do look e `acessorios_sugeridos` (até 4, opcionais), obrigatórios na resposta; `minItems: 3` e `maxItems: 5`.
- [x] Menos de 3 looks conta como resposta inválida (uma nova tentativa); acima de 5, corta.
- [x] Prompt: looks realmente diferentes entre si, avaliação mais exigente com problemas concretos.
- [x] `looks_recentes` no contexto (até 8: looks salvos em `meusLooks` + looks já sugeridos na sessão), só com chaves do armário; falha ao ler `meusLooks` não impede a geração.
- [x] Validação descarta look com as mesmas peças do armário (2+) de um recente ou de outro da mesma resposta.
- [x] Interface: descrição no topo do card e acessórios como etiquetas.
- [x] Testes (MOCK): schema, 2 looks → nova tentativa e falha, 7 → 5, textos cortados, repetição descartada, contexto de recentes. `pytest` 142 passed.
- [ ] Confirmar na chamada real (Etapa 8) que a API aceita `minItems`/`maxItems` no schema.

### Validação real (Etapa 8)
- [ ] Confirmar no AI Studio que o projeto está no Free Tier e sem faturamento.
- [ ] Uma única chamada real de texto com `gemini-3.8-flash`, confirmando schema, formato e latência.
