# Design Técnico — 024-contexto-climatico

## Visão Geral da Arquitetura

```text
/look-do-dia ─► WardrobeLifeState.load_weather_context (servidor Reflex)
                   │ endereço padrão (Xano/SQLite: consultaEnderecoDoCliente)
                   ▼
              OSDroupa/ai/weather.py
                   ├─ geocode(cidade, uf)      → geocoding-api.open-meteo.com/v1/search
                   ├─ forecast(lat, lon)       → api.open-meteo.com/v1/forecast
                   └─ build_context(...)       → WeatherContext (dict serializável)
```

A consulta roda no servidor Reflex. A Open-Meteo não exige chave, e nenhum dado pessoal além da cidade é enviado a ela. Seguindo a decisão aprovada, a lógica de integração externa fica no servidor Reflex; Xano e SQLite continuam responsáveis apenas pela persistência.

## Contratos externos (Open-Meteo)

- **GET** `https://geocoding-api.open-meteo.com/v1/search?name=<cidade>&countryCode=BR&language=pt&count=10`
  - O resultado é filtrado por `admin1` correspondente à UF quando informada.
- **GET** `https://api.open-meteo.com/v1/forecast?latitude=..&longitude=..&timezone=auto&forecast_days=1`
  - `current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,is_day`
  - `hourly=precipitation_probability`
  - `daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,uv_index_max`
- Timeout de 8 s, sem retry automático. Erros HTTP e de JSON viram `WeatherUnavailable`.

## Contrato interno — `WeatherContext`

```python
{
  "cidade": "Recife", "uf": "PE", "regiao": "Nordeste",
  "temperatura": 29.1, "sensacao": 33.0, "minima": 24.8, "maxima": 30.2,
  "umidade": 74, "chuva_prob": 40, "chuva_mm": 0.0, "vento_kmh": 14.0, "uv_max": 9.5,
  "condicao": "Parcialmente nublado", "weather_code": 2,
  "data_local": "2026-11-02", "hora_local": "14:10", "periodo": "Tarde",
  "estacao": "Primavera", "categoria": "Quente",
  "fonte": "Open-Meteo", "consultado_em": "2026-11-02T17:10:00Z", "manual": False
}
```

- `regiao` vem de uma tabela fixa UF → região (as 27 UFs).
- `estacao` vem de datas astronômicas aproximadas para o hemisfério sul. Como no Norte e no Nordeste as estações clássicas descrevem mal o clima, o contexto enviado à IA (Change 025) prioriza a previsão real.
- `condicao` vem de uma tabela fixa dos códigos WMO para textos em pt-BR.

## Modelo de Estado e UI (Reflex)

- **Estado (`WardrobeLifeState`):** `weather_context: dict[str, str]`, `weather_city_query: str`, `weather_loading: bool`, `weather_notice: str`.
- **Eventos:** `load_weather_context` (chamado no `on_load` de `/look-do-dia`, antes de `load_daily_look`), `search_weather_city`, `use_manual_weather`.
- `daily_weather` recebe `weather_context["categoria"]` quando a previsão estiver disponível. O select manual continua existindo e, ao ser alterado, marca `manual=True`.
- **UI:** cartão "Clima agora em <cidade>" com ícone da condição, temperatura e sensação, chuva, umidade e UV, mais o rodapé "Fonte: Open-Meteo · atualizado às HH:MM". Campo de busca de cidade.

## Decisões Arquiteturais e Integridade

1. **Open-Meteo em vez de OpenWeatherMap:** dispensa chave, é gratuita para uso não comercial, cobre o Brasil e oferece sensação térmica e probabilidade de chuva horária. Para uso comercial é preciso contratar o plano pago, o que fica registrado como pendência de lançamento.
2. **Cidade do endereço em vez de GPS:** reaproveita um dado que já existe e mantém a promessa atual da política de privacidade. O texto da política será ajustado para citar o envio da cidade a um serviço de clima.
3. **Cache em memória por processo** (chave `lat,lon` arredondada a 2 casas, TTL 30 min): reduz latência e chamadas. Não é persistido porque o clima expira rapidamente.
4. **Novo pacote `OSDroupa/ai/`** só com serviços sem UI, para não aumentar o arquivo principal. States e páginas continuam em `OSDroupa.py`.
5. **Compatibilidade:** a categoria derivada alimenta o `lookDoDia` existente, sem mudar os contratos Xano e SQLite.
