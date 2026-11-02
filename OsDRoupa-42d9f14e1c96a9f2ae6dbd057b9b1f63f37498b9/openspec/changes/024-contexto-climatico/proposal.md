# Proposta — 024-contexto-climatico

## Contexto

O Look do Dia (`/look-do-dia`) pede que a pessoa escolha manualmente o clima entre Quente, Ameno, Frio e Chuvoso. A própria tela informa que a previsão não é consultada. Com isso, a recomendação ignora a temperatura real, a sensação térmica, a chuva e a umidade, que variam muito entre as regiões do Brasil. O endereço padrão da conta (CEP, cidade e UF) já está cadastrado e pode servir como localização.

## Objetivo

Fornecer ao Look do Dia, e às próximas changes de IA, um contexto climático real e normalizado da localização da pessoa, mantendo a escolha manual como alternativa quando a previsão não estiver disponível.

## Escopo incluído

- Serviço Python no servidor Reflex que consulta a previsão na API pública Open-Meteo (forecast + geocoding), sem chave.
- Localização obtida da cidade e UF do endereço padrão, ou de uma cidade informada na tela.
- Contexto normalizado: temperatura, sensação térmica, mínima/máxima do dia, probabilidade e volume de chuva, umidade, vento, índice UV, condição (`weather_code`), data/hora local, período do dia, estação astronômica do hemisfério sul e região brasileira (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).
- Classificação do contexto nas categorias atuais (Quente/Ameno/Frio/Chuvoso) para a heurística existente do `lookDoDia` continuar funcionando.
- Cartão de clima em `/look-do-dia`, com fonte, cidade e horário da consulta.
- Cache em memória por localização (30 min) e fallback para a escolha manual.

## Escopo excluído

- Geolocalização do navegador (GPS); fica para uma change futura, com consentimento explícito.
- Geração de looks por IA (Change 025).
- Persistência do histórico climático no Xano ou no SQLite.
- Alertas meteorológicos oficiais (Defesa Civil/INMET).

## Dependências e impactos

- **Modelagem de dados:** nenhuma tabela nova. Leitura do endereço padrão já existente (`consultaEnderecoDoCliente`).
- **APIs:** nenhum endpoint Xano novo. O parâmetro `clima` de `lookDoDia` continua aceitando as quatro categorias.
- **Frontend:** `WardrobeLifeState` e página `/look-do-dia`. O texto da política de privacidade (`/privacidade`) passa a citar o uso da cidade do endereço para consultar o clima.
- **Integrações externas:** Open-Meteo (`api.open-meteo.com/v1/forecast` e `geocoding-api.open-meteo.com/v1/search`).
