# Design Técnico — 027-visualizacao-looks

## Visão Geral da Arquitetura

```text
card da proposta ─► look_visual(proposal)
   ├─ quadro: rx.foreach(proposal.pecas, look_board_tile)        (sem rede, sem custo)
   └─ "Gerar imagem do look" ─► WardrobeLifeState.generate_look_image (background)
          └─ OSDroupa/ai/imaging.py
               ├─ load_reference(url)   data URI | /assets local | HTTPS público (anti-SSRF)
               ├─ build_prompt(...)
               └─ genai.Client().aio.interactions.create(model, input=[imagens..., texto], response_format=imagem)
                    └─ grava em rx.get_upload_dir()/looks/<uuid>.png → proposal.imagem_gerada
```

## Integração com o Google

- SDK `google-genai==2.34.0`, cliente `genai.Client(api_key=GEMINI_API_KEY)`, chamada assíncrona `client.aio.interactions.create`, conforme a documentação atual de geração de imagens ("Nano Banana"), que usa a Interactions API.
- Modelo padrão `gemini-nano-banana-2.1` (recomendado pela documentação para projetos novos; aceita até 10 imagens de objeto como referência). Configurável por `OSDROUPA_IMAGE_MODEL`, por exemplo `gemini-3.1-flash-lite-image` para reduzir custo, sabendo que ele não é otimizado para várias referências.
- Entrada: lista de partes `{"type": "image", "data": <base64>, "mime_type": ...}` seguida de `{"type": "text", "text": prompt}`.
- `response_format={"type": "image", "aspect_ratio": "3:4", "image_size": "1K"}`: retrato para look de corpo inteiro, em 1K para equilibrar qualidade e custo.
- Saída: `interaction.output_image.data` (base64) e `mime_type`.
- Erros: `google.genai.errors.ClientError` (429 → "muito requisitado"; demais → "recusou"), `APIError`/`httpx.HTTPError` → "indisponível"; `asyncio.wait_for` de 120 s.

## Segurança

- Chave lida só no servidor, nunca registrada em log.
- Referências remotas: apenas `https`, resolução DNS conferida com `ipaddress.is_global` para todos os endereços, `follow_redirects=False`, leitura em stream interrompida acima de 4 MB e `content-type` restrito a PNG/JPEG/WebP. Limitação conhecida: entre a checagem de DNS e a conexão existe uma janela de *DNS rebinding*; para produção, considere um proxy de saída com allowlist.
- Assets locais: caminho resolvido precisa ficar dentro de `assets/` (bloqueia `../`).
- `uploaded_files/` foi adicionado ao `.gitignore`.

## Estado e UI

- `LookProposal.imagem_gerada` guarda o caminho relativo `looks/<arquivo>`; o componente usa `rx.get_upload_url(...)`.
- `WardrobeLifeState.image_loading_id` garante uma geração por vez por sessão e mostra o carregamento no card certo; `image_ai_enabled` (computed var) mostra o botão só quando a chave existe.
- Cota própria por conta via `stylist.reserve_generation("img:<id>", limit=...)`.

## Decisões

1. **Composição real como base:** é a única visualização fiel ao armário e funciona sem custo; a imagem gerada é complementar e rotulada.
2. **Manequim invisível, sem pessoas:** evita gerar rostos ou corpos, o que tira as questões de semelhança com pessoas reais e de representação de corpo.
3. **Imagem não persistida no banco:** a persistência entra com o feed (028), junto com o modelo de dados de looks salvos e publicados.
