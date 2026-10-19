# Especificações Consolidadas do Sistema (openspec/specs/)

Este diretório contém o **comportamento consolidado e a fonte de verdade** do sistema OSDroupa.

> **Regra Fundamental (Manual do Professor — Seção 31):**
> Este diretório **NÃO DEVE** ser preenchido manualmente no início do projeto.
>
> Inicialmente, ele permanece vazio. Conforme cada **Change** é implementada, verificada e arquivada (`Archive`), o OpenSpec promove os requisitos e comportamentos consolidados de `openspec/changes/<change-id>/specs/` para este diretório.

## Estrutura futura esperada

Conforme as changes forem concluídas e arquivadas, surgirão especificações modulares, por exemplo:
- `auth/spec.md`: Especificação de autenticação e sessão.
- `cliente/spec.md`: Especificação do perfil e dados do cliente.
- `catalogo/spec.md`: Especificação de produtos e roupas.
- `pedidos/spec.md`: Especificação do fluxo de pedidos.

Cada especificação consolidada reflete o estado atual em produção/implementação, com requisitos funcionais e cenários verificáveis.

- [Gestão de Endereços e CEP](./addresses/spec.md)
