# Estrutura do repositório

O repositório mantém os caminhos esperados pelo Reflex e organiza documentação, histórico e backend por responsabilidade. Antes de mover um diretório, confira se ele não é um caminho de runtime descrito abaixo.

## Pastas mantidas na raiz

| Pasta | Responsabilidade | Regra |
|---|---|---|
| `OSDroupa/` | Aplicação Reflex: estados, componentes, rotas e integrações HTTP; `env.py` carrega o `.env`; `daily_look.py` é o plano B do Look do Dia | Não mover sem atualizar imports e `rxconfig.py`. |
| `OSDroupa/ai/` | Clima (Open-Meteo), estilista, limites de uso, imagem e `providers/` (Gemini) | Só roda no servidor; nada daqui vai para o navegador. |
| `tests/` | Testes `pytest` com SQLite temporário e provedores falsos; marcador `live` para chamadas reais | `pytest` padrão nunca chama APIs reais nem usa `data/`. |
| `assets/` | Imagens, fontes, SVGs e arquivos publicados pelo Reflex | Deve permanecer na raiz para o servidor de assets. |
| `xano/table/` | Schemas XanoScript das tabelas | Fonte versionada do modelo físico Xano. |
| `xano/api/` | Endpoints XanoScript agrupados por API | Fonte versionada dos contratos e regras do backend. |
| `openspec/changes/` | Changes ativas (023 a 030) e histórico arquivado | Situação de cada uma em `openspec/changes/README.md`. |
| `openspec/specs/` | Especificações canônicas já promovidas | Atualizar quando uma change for concluída e arquivada. |
| `docs/` | Modelo de domínio, visão geral, roteiro e documentação | Conteúdo de arquitetura e apresentação. |
| `professormateria/` | Backend SQLite local, seed de catálogo e material acadêmico | SQLite é apoio local; Xano é o backend da entrega. |
| `logs/` | Logs históricos de execução (todos já movidos da raiz) | Não usar como saída permanente de novos builds. |

## Pastas locais e geradas

`.venv/`, `.web/`, `.states/`, `reflex.lock/`, `data/`, `uploaded_files/`, `tmp/`, `output/`, `.agents/` e `__pycache__/` são ambiente virtual, arquivos gerados, dados locais ou suporte a ferramentas. Permanecem nos caminhos atuais para não quebrar Reflex, configuração ou dados de desenvolvimento. `data/` e segredos ficam fora do controle de versão.

## Convenções

- Novas funcionalidades ganham uma change numerada em `openspec/changes/` e uma linha no índice; pendências gerais continuam na Change 023.
- Manter requisitos e decisões separados por domínio dentro da Change 023 (`specs/` e `design/modules/`).
- Arquivar changes antigas em `openspec/changes/archive/`; a cópia arquivada é a fonte histórica e preserva checklists originais.
- Novos logs de execução devem ir para diretório temporário local.
- Segredos só no `.env` da raiz (ignorado pelo Git); `.env.example` lista os nomes sem valores.
- Não mover `assets/`, tabelas/endpoints Xano ou o pacote Reflex como parte de uma arrumação documental.