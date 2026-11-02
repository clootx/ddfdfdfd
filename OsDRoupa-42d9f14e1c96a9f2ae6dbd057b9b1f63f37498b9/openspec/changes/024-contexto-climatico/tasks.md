# Tarefas — 024-contexto-climatico

## Status: IMPLEMENTADA; VALIDAÇÃO NO NAVEGADOR PENDENTE

### OpenSpec
- [x] Registrar proposta, requisitos, design e tarefas.
- [x] Registrar a change no índice `openspec/changes/README.md`.

### Serviço (Python)
- [x] Criar `OSDroupa/ai/__init__.py` e `OSDroupa/ai/weather.py` com `geocode`, `forecast` e `build_context`. Validado com chamadas reais para Recife/PE, Manaus/AM, Porto Alegre/RS e São Paulo.
- [x] Mapear UF → região, códigos WMO → texto pt-BR e data → estação do hemisfério sul. Validado: as 27 UFs mapeadas e as fronteiras das estações testadas.
- [x] Implementar a categoria (RF-CLIMA-03), o timeout, `WeatherUnavailable` e o cache de 30 min (previsão) e de cidades (geocoding). Validado: limites de 17/27 °C, chuva ≥ 60%, precipitação atual, código WMO chuvoso, cidade inexistente e timeout de rede.

### Estado (Reflex)
- [x] Adicionar `weather_context`, `weather_city_query`, `weather_loading`, `weather_notice`, `has_weather`, `load_weather_context` e `search_weather_city` em `WardrobeLifeState`. O `on_load` de `/look-do-dia` executa `load_weather_context` antes de `load_daily_look`.
- [x] Ler a cidade e UF do endereço padrão via `consultaEnderecoDoCliente` (`_cep.cidade`/`_cep.uf`), o mesmo contrato usado no checkout, nos modos Xano e SQLite.

### Interface
- [x] Criar o cartão de clima, a busca de cidade ("Cidade/UF") e os estados de carregamento, aviso e escolha manual.
- [x] Atualizar o texto de `/look-do-dia` e da política de privacidade sobre o envio de cidade/UF à Open-Meteo.

### Verificação
- [x] Compilar o Reflex sem erros (`reflex compile`, 98 páginas).
- [ ] Executar os cenários 1–6 da spec no navegador, nos modos SQLite e Xano, com contas de teste.
- [ ] Confirmar no navegador que a sugestão manual atual continua funcionando.

### Pendência de lançamento
- [ ] Contratar o plano comercial da Open-Meteo antes de uso comercial (o plano gratuito é para uso não comercial).
