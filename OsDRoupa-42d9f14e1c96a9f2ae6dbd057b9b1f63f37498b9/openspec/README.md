# OpenSpec — Ambiente e Guia de Uso

Este diretório contém a estrutura oficial de especificação e evolução incremental do projeto **OSDroupa**, iniciado em **14/09/2026**, estruturado de acordo com a metodologia ensinada no manual do professor (`professormateria/Preparação de um Projeto com OpenSpec.md`).

---

## 1. O Princípio Fundamental

> **Primeiro fornecer contexto suficiente para a IA compreender o projeto; depois desenvolver o sistema de forma incremental com fatias verticais.**

O sistema não deve ser gerado de uma só vez nem ter seu banco de dados implementado antecipadamente de forma isolada. O desenvolvimento avança por **Changes** pequenas, delimitadas e verificáveis.

---

## 2. Estrutura Atual de Pastas e Arquivos

```text
openspec/
├── config.yaml          # Configuração dos workflows (spec-driven, context, rules, operations)
├── README.md            # Este guia explicativo do ambiente
├── specs/               # Especificações consolidadas do sistema (fonte de verdade após Archive)
│   ├── README.md
│   ├── auth/
│   │   └── spec.md      # Especificação definitiva de autenticação e sessão
│   └── cliente/
│       └── spec.md      # Especificação definitiva do perfil de cliente
├── changes/             # Mudanças em planejamento ou implementação
│   ├── 002-auth-landing-page/ # Change 002 (Refatoração da Página Inicial - Entrar e Cadastro)
│   │   ├── proposal.md
│   │   ├── specs/auth-landing.md
│   │   ├── design.md
│   │   └── tasks.md
│   ├── 003-address-and-cep/   # Change 003 (Próxima: Gestão de Endereços e CEP)
│   │   ├── proposal.md
│   │   ├── specs/address-and-cep.md
│   │   ├── design.md
│   │   └── tasks.md
│   └── archive/         # Histórico de changes concluídas
│       └── 001-foundation-identity-client/
│           ├── proposal.md
│           ├── specs/auth-and-client.md
│           ├── design.md
│           └── tasks.md
└── templates/           # Modelos padronizados para criação de novas changes
    ├── README.md
    ├── proposal.template.md
    ├── spec.template.md
    ├── design.template.md
    └── tasks.template.md
```

---

## 3. Comandos e Workflows do OpenSpec

O OpenSpec opera através de um loop principal de 5 etapas:

### 1. `openspec init`
Inicializa o OpenSpec no repositório, cria a pasta `openspec/` com `config.yaml`, `specs/` e `changes/archive/`, e instala os prompts/workflows na ferramenta de IA selecionada.

### 2. `Explore` (Investigação e Decomposição)
- **Quando usar:** Antes de propor qualquer change ou código.
- **O que faz:** O agente lê os documentos de contexto (`docs/project-overview.md`, `docs/domain-model.md`, `openspec/config.yaml`), investiga o repositório, mapeia dependências entre módulos e propõe uma ordem lógica de fatias verticais.
- **Regra:** Não cria código nem altera o banco de dados.

### 3. `Propose` (Proposta da Change)
- **Quando usar:** Quando a ideia investigada no Explore estiver madura para implementação.
- **O que faz:** Cria a pasta `openspec/changes/<change-id>/` com os 4 artefatos padrão do schema `spec-driven`:
  1. `proposal.md`: Contexto, objetivo, escopo delimitado e dependências.
  2. `specs/`: Requisitos funcionais verificáveis e cenários BDD (`Dado / Quando / Então`).
  3. `design.md`: Desenho técnico, integração Reflex (Python) e Xano (Backend), contratos de API e modelos.
  4. `tasks.md`: Checklist sequencial de pequenas tarefas de implementação.

### 4. `Review` (Revisão Humana Obrigatória)
- **Quando usar:** Antes de autorizar qualquer linha de código.
- **Princípio:** *"IA propõe → Aluno analisa → Aluno aprova/corrige → IA implementa"*.

### 5. `Apply` (Implementação Incremental)
- **Quando usar:** Após aprovação do Review.
- **O que faz:** O agente implementa estritamente as tarefas descritas em `tasks.md`, marcando os checkboxes conforme cada tarefa for executada e validada.

### 6. `Verify` (Verificação de Aceitação)
- **Quando usar:** Ao término das tarefas do `tasks.md`.
- **O que faz:** Testa os cenários de aceitação (Gherkin) descritos na especificação para garantir que a funcionalidade foi entregue sem quebrar o sistema.

### 7. `Archive` (Conclusão e Consolidação)
- **Quando usar:** Quando a change estiver totalmente implementada e verificada.
- **O que faz:**
  1. Move `openspec/changes/<id>/` para `openspec/changes/archive/<id>/`.
  2. Promove e consolida as especificações definitivas para `openspec/specs/`.
