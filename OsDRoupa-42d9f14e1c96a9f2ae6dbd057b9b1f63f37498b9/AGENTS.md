# Instruções para Agentes de IA — OSDroupa

<!-- reflex managed begin (do not edit inside this block; add custom content outside the markers) -->
# Agents

This project uses the **Reflex agent skills** - up-to-date knowledge for building full-stack Python web apps with [Reflex](https://reflex.dev). Install them first, then use them as described below.

## Installing the Skills

Before working on this project, make sure the Reflex skills are available to you.

### Claude Code

If the skills are not already available, install them yourself by running these shell commands:

```bash
claude plugin marketplace add reflex-dev/agent-skills
claude plugin install reflex@reflex-agent-skills
```

Newly installed plugins load on the next session. After installing, tell the user to restart the session so the skills auto-load; until then, read the skill files directly from `~/.claude/plugins/` when you need them.

### Other agents (Cursor, OpenCode, Codex, Pi)

```
npx skills add reflex-dev/agent-skills
```

Or clone https://github.com/reflex-dev/agent-skills and copy the `skills/` folders into your agent's skill directory (see the repo README for paths).

### Verifying

Before writing or editing any Reflex code, confirm these three skills are available: `reflex-docs`, `setup-python-env`, and `reflex-process-management`. If they are not, STOP and run the install step above - do not proceed without them.

## Using the Skills

### Reflex documentation

For anything about Reflex APIs - components, state management, events, styling, database, routing, authentication - use the **reflex-docs** skill rather than relying on memory. It carries current, version-accurate docs.

### Initializing a new Reflex project

When starting a new Reflex project or setting up a development environment, you **must** follow the **setup-python-env** skill before doing anything else.

Do not skip any steps. Do not assume a virtual environment or Reflex is already available - always verify first by following the skill's instructions in order.

After the environment is ready and Reflex is installed, run:

```bash
reflex init
```

Then proceed with the user's request.

### Managing a Reflex process

When you need to compile, run, reload, or debug a Reflex application, follow the **reflex-process-management** skill for the correct sequence and error investigation steps.
<!-- reflex managed end -->

---

# Diretrizes Operacionais do Projeto

## Visão Geral do Projeto

Este repositório combina:
- **Reflex** para a interface web em Python (UI componentizada e reativa).
- **Xano e XanoScript** para backend, regras de negócio, autenticação e banco de dados PostgreSQL.
- **OpenSpec** para especificação de contratos e evolução incremental guiada por mudanças (Changes).
- **Python e IA** para módulos de recomendação de looks, visão computacional e automações.

O objetivo do projeto é evoluir de forma incremental, com foco em entregas pequenas, verificáveis e estritamente alinhadas ao domínio de negócio.

## Princípios Fundamentais de Trabalho

1. **Contexto antes de código:** Não implementar funcionalidades sem antes validar o contexto do domínio (`docs/domain-model.md`, `docs/project-overview.md` e `openspec/config.yaml`).
2. **Fatias verticais:** Priorizar mudanças que entreguem valor de ponta a ponta: dados + regras + API + frontend Reflex.
3. **Evolução do banco orientada a funcionalidade:** A evolução do schema no Xano deve acompanhar a necessidade da funcionalidade, e não ser implementada antecipadamente de forma isolada.
4. **Análise de dependências:** Antes de criar ou alterar uma feature, validar dependências entre modelo, autenticação, regras de negócio e integrações.
5. **Respeito ao domínio global:** Preservar a consistência entre cliente, usuário, produto, pedido, status, transação, produção e integrações externas.
6. **Ciclo OpenSpec obrigatório:** Trabalhar em ciclos pequenos:
   Explore -> Propose -> Review -> Apply -> Verify -> Archive.
7. **Revisão humana antes de implementar:** O agente propõe, o desenvolvedor analisa/aprova e o agente implementa.

## Estrutura do Repositório

- `OSDroupa.py`: Aplicação Reflex (página principal e componentes reativos).
- `rxconfig.py`: Configuração da aplicação Reflex (plugins Tailwind, Radix).
- `OSDroupa/`: Módulo da aplicação Reflex.
- `docs/`: Documentos de contexto global (`project-overview.md`, `domain-model.md`).
- `openspec/`: Configurações de especificação, specs consolidadas e changes ativas.
- `xano/table/`: Modelos de dados no Xano.
- `xano/api/`: Grupos e endpoints da API do Xano.
- `xano/addon/`: Funções e integrações auxiliares.
- `xano/function/`: Funções reutilizáveis no backend.

## Regras de Código e Arquitetura

- **Frontend (Reflex):** Utilizar estados (`rx.State`), componentes reativos e tokens de design. O frontend nunca deve ser considerado barreira de segurança.
- **Backend (Xano):** Toda regra de negócio crítica, permissão e autenticação deve ser validada e persistida no Xano.
- **Contratos:** Requisições autenticadas devem trafegar com `Authorization: Bearer <token>` em conformidade com as especificações da Change.
- **Idioma:** Toda documentação, artefatos OpenSpec e mensagens de commit devem ser redigidos em português brasileiro.
