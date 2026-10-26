# Proposta — 021-experiencia-cliente-completa

## Problema

As páginas de perfil e fidelidade exibem poucos dados e a loja não oferece uma lista de favoritos. O checkout já usa Mercado Pago Orders no backend local, mas apresenta pouco contexto sobre itens, subtotal estimado, etapas e confirmação. O fluxo precisa comunicar melhor o que a pessoa pode fazer e quais partes dependem da configuração operacional.

## Objetivo

Completar os fluxos de perfil, desafios, fidelidade, loja e checkout usando os contratos existentes, persistindo preferências opcionais por conta e mantendo o Mercado Pago como meio de pagamento externo.

## Escopo

- Perfil autenticado com edição de dados pessoais e preferências de estilo e tamanho, com validação e persistência SQLite.
- Contrato XanoScript de perfil e campos complementares no cadastro de cliente para futura publicação remota.
- Catálogo de oito desafios categorizados, com filtros, links para as atividades e progresso visível.
- Fidelidade com cinco níveis, progresso para o próximo nível e histórico de pontos por desafio concluído.
- Favoritos da loja persistidos no navegador e isolados por conta, com filtro e controles em cards/detalhe.
- Checkout com revisão dos itens, subtotal claramente estimado, etapas de entrega e pagamento e explicação do redirecionamento seguro ao Mercado Pago.
- Atualização dos artefatos OpenSpec e limites descritos sem sugerir resgate monetário de pontos nem pagamento real sem credenciais.

## Fora do escopo

- Alterar e-mail ou senha sem fluxo próprio de verificação.
- Guardar número de cartão ou coletar dados de pagamento no OSDROUPA.
- Garantir que Pix ou cartão estejam habilitados na conta Mercado Pago.
- Inventar avaliação, desconto, estoque, frete, prazo ou dados de produto.
- Promover SQLite local para banco multi-instância de produção.

## Critério de conclusão

Uma pessoa consegue editar e recuperar seus campos de perfil, explorar desafios por categoria e andamento, acompanhar nível e histórico, salvar favoritos sem misturar contas, revisar a sacola antes de sair para o pagamento e distinguir o pedido demonstrativo do pedido Mercado Pago pendente de confirmação pelo webhook.
