# Estrutura do repositório

O repositório mantém os caminhos esperados pelo Reflex e organiza documentação, histórico e backend por responsabilidade. Antes de mover um diretório, confira se ele não é um caminho de runtime descrito abaixo.

## Pastas mantidas na raiz

| Pasta | Responsabilidade | Regra |
|---|---|---|
| `OSDroupa/` | Aplicação Reflex: estados, componentes, rotas e integrações HTTP | Não mover sem atualizar imports e `rxconfig.py`. |
| `assets/` | Imagens, fontes, SVGs e arquivos publicados pelo Reflex | Deve permanecer na raiz para o servidor de assets. |
| `xano/table/` | Schemas XanoScript das tabelas | Fonte versionada do modelo físico Xano. |
| `xano/api/` | Endpoints XanoScript agrupados por API | Fonte versionada dos contratos e regras do backend. |
| `openspec/changes/` | Change ativa e histórico arquivado | Uma única change ativa: `023-consolidacao-geral-do-projeto`. |
| `openspec/specs/` | Especificações canônicas já promovidas | Atualizar quando uma change for concluída e arquivada. |
| `docs/` | Modelo de domínio, visão geral, roteiro e documentação | Conteúdo de arquitetura e apresentação. |
| `professormateria/` | Backend SQLite local, seed de catálogo e material acadêmico | SQLite é apoio local; Xano é o backend da entrega. |
| `logs/` | Logs históricos movidos da raiz; seis arquivos bloqueados ficam temporariamente na raiz | Não usar como saída permanente de novos builds. |

## Pastas locais e geradas

`.venv/`, `.web/`, `.states/`, `reflex.lock/`, `data/`, `uploaded_files/`, `tmp/`, `output/`, `.agents/` e `__pycache__/` são ambiente virtual, arquivos gerados, dados locais ou suporte a ferramentas. Permanecem nos caminhos atuais para não quebrar Reflex, configuração ou dados de desenvolvimento. `data/` e segredos ficam fora do controle de versão.

## Convenções

- Não criar outra pasta ativa em `openspec/changes/`; novas tarefas entram na Change 023 até ela ser encerrada.
- Manter requisitos e decisões separados por domínio dentro da Change 023 (`specs/` e `design/modules/`).
- Arquivar changes antigas em `openspec/changes/archive/`; a cópia arquivada é a fonte histórica e preserva checklists originais.
- Novos logs de execução devem ir para diretório temporário local; os seis logs presos podem ser movidos após encerrar seus processos.
- Não mover `assets/`, tabelas/endpoints Xano ou o pacote Reflex como parte de uma arrumação documental.