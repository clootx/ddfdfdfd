# Templates de Change do OpenSpec (schema: spec-driven)

Este diretório contém modelos de referência para criação de novas mudanças (**Changes**) no projeto OSDroupa.

## Como criar uma nova Change:

1. Crie uma pasta dentro de `openspec/changes/` com o padrão:
   `openspec/changes/<id-sequencial>-<slug-da-funcionalidade>/`
   *(Exemplo: `openspec/changes/002-address-and-cep/`)*

2. Copie e preencha os 4 artefatos padrão a partir destes templates:
   - `proposal.template.md` -> `openspec/changes/<pasta>/proposal.md`
   - `spec.template.md` -> `openspec/changes/<pasta>/specs/<modulo>.md`
   - `design.template.md` -> `openspec/changes/<pasta>/design.md`
   - `tasks.template.md` -> `openspec/changes/<pasta>/tasks.md`

3. Siga o fluxo OpenSpec:
   `Explore` -> `Propose` -> `Review` -> `Apply` -> `Verify` -> `Archive`
