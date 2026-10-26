# Design — 023-consolidacao-geral-do-projeto

## Arquitetura de referência

- **Interface:** Reflex/Python em `OSDroupa/`; páginas, componentes, estado visual e navegação permanecem no frontend.
- **Backend da entrega:** Xano e XanoScript em `xano/`. Autenticação, autorização, regras críticas e dados compartilhados são responsabilidade do Xano.
- **Desenvolvimento local:** SQLite em `professormateria/local_backend.py` continua opcional para execução offline. Não é a fonte de verdade da apresentação.
- **Pagamentos:** Mercado Pago Orders é o fluxo atual. Os endpoints Asaas antigos são histórico/inativos e não devem ser reativados nesta consolidação.
- **Integrações externas:** SMTP/SendGrid, Mercado Pago e hardware IoT só são considerados prontos quando configuração e exercício real forem registrados como concluídos.
- **Gestão de mudanças:** esta pasta 023 passa a ser a única change ativa. As pastas anteriores ficam em `archive/` como fontes históricas; apenas pendências não supersedidas permanecem nesta tasks.md.

## Organização física

Os diretórios convencionais do Reflex, Xano e OpenSpec não mudam de nome nem de localização. A organização separa documentação de produto (`docs/`), especificações da change (`specs/`), decisões por módulo (`design/modules/`), histórico (`openspec/changes/archive/`) e logs de execução (`logs/`).

```text
.
├── OSDroupa/                 # aplicação Reflex
├── assets/                   # imagens e fontes servidas pelo Reflex
├── docs/                     # arquitetura, domínio, roteiro e estrutura
├── logs/                     # logs preservados de execuções locais
├── openspec/
│   ├── changes/023-.../      # única change ativa
│   │   ├── design/modules/   # decisões técnicas por domínio
│   │   ├── specs/            # requisitos originais organizados por módulo
│   │   └── tasks.md          # checklists consolidados com estado preservado
│   ├── changes/archive/      # changes anteriores preservadas como histórico
│   └── specs/               # contratos canônicos já promovidos
├── professormateria/         # backend local, dados de demonstração e material acadêmico
├── xano/api/                 # endpoints XanoScript
└── xano/table/               # tabelas XanoScript
```

Os diretórios `.venv/`, `.web/`, `.states/`, `data/`, `uploaded_files/`, `reflex.lock/`, `tmp/` e `output/` são locais ou gerados pelo ambiente. Eles permanecem nos caminhos atuais para não quebrar ferramentas, configuração ou dados locais.

## Módulos reunidos

A change preserva os requisitos por domínio: autenticação e sessão; endereços; perfil e armário; loja e catálogo; checkout/pedidos/pagamentos; gestão; conteúdo, desafios e fidelidade; IoT; looks e calendário; confiabilidade; backend local; experiência de cliente; e boutiques demonstrativas. Cada fonte original fica acessível em um subdiretório próprio de `specs/` e `design/modules/`.

## Regras para reconciliar decisões antigas

1. As tarefas concluídas permanecem marcadas nas cópias históricas arquivadas; as tarefas abertas são trazidas para este tasks.md sem reclassificação.
2. Toda tarefa aberta é copiada como aberta. A seção de origem na tasks.md aponta para a pasta arquivada correspondente.
3. Referências de Asaas são preservadas como histórico, mas a execução atual segue Mercado Pago, conforme a Change 020.
4. SQLite continua documentado como opção local, mas o caminho de apresentação usa `OSDROUPA_BACKEND=xano`.
5. Não há publicação automática: scripts `.xs` no repositório não significam que o workspace remoto recebeu a alteração.

## Compatibilidade

A consolidação altera documentação e localização de arquivos de planejamento e logs. Não altera imports Python, URLs, nomes de tabela, contratos de API, localização dos assets nem configuração de execução do Reflex.