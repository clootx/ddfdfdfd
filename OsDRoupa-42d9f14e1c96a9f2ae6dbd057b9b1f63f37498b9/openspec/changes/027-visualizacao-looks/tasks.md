# Tarefas — 027-visualizacao-looks

## Status: IMPLEMENTADA; TESTE COM CHAVE REAL E NAVEGADOR PENDENTES

### OpenSpec
- [x] Registrar proposta, requisitos, design e tarefas.
- [x] Registrar a change no índice `openspec/changes/README.md`.

### Configuração
- [x] Adicionar `google-genai==2.34.0` ao `requirements.txt`; instalação validada junto com Reflex e anthropic.
- [x] Adicionar `GEMINI_API_KEY`, `OSDROUPA_IMAGE_MODEL` e `OSDROUPA_IMAGES_PER_HOUR` ao `.env.example`.
- [x] Ignorar `uploaded_files/` no Git.

### Serviço (Python)
- [x] Criar `OSDroupa/ai/imaging.py` com `load_reference`, `build_prompt` e `generate_look_image`.
- [x] Proteção anti-SSRF e de caminho. Validado com testes: http, localhost, 127.0.0.1, IP privado, 169.254.169.254, ftp, file e `../` bloqueados; data URI inválido ou de tipo não permitido recusado.
- [x] Tratamento de erros. Validado com cliente simulado: sem chave, resposta sem imagem, 429 e 503; arquivo gravado com o conteúdo devolvido.
- [x] Generalizar `stylist.reserve_generation` com parâmetro `limit` (cota separada para imagens).

### Estado e interface
- [x] `LookProposal.imagem_gerada`, `WardrobeLifeState.generate_look_image` (background), `image_loading_id` e `image_ai_enabled`.
- [x] `look_visual` com quadro de composição, botão, carregamento e imagem rotulada nos cards da IA.
- [x] Atualizar a política de privacidade (envio de descrições e fotos ao Google).

### Verificação
- [x] Compilar o Reflex sem erros; regressão dos testes da 025 e da 026.
- [ ] Gerar uma imagem real com `GEMINI_API_KEY` e confirmar que `aspect_ratio: "3:4"` é aceito pelo modelo padrão (a documentação lida citava 1:1, 16:9 e 5:4 explicitamente).
- [ ] Executar os cenários 1–5 da spec no navegador.
- [ ] Conferir o preço por imagem na página de preços da API Gemini antes de definir a cota de produção.
