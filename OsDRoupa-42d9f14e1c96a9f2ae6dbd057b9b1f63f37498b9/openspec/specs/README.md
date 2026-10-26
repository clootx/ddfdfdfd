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
- [Páginas institucionais e responsividade](./institutional-pages/spec.md)
- [Sistema visual e navegação](./design-system/spec.md)
- [Pedidos e pagamentos atualizados para Mercado Pago](./orders-payments/spec.md)
- [Requisitos da Change 020 — armário vivo, fidelidade e privacidade](../changes/archive/020-armario-vivo-loyalty-mercadopago/specs/armario-vivo/spec.md)

As especificações e decisões ainda em andamento estão reunidas na única change ativa: [023 — consolidação geral do projeto](../changes/023-consolidacao-geral-do-projeto/).
