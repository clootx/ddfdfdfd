# Proposta — 020-armario-vivo-loyalty-mercadopago

## Problema

O projeto tem armário, looks, calendário, desafios e pedido demonstrativo, mas ainda não conecta essas áreas em uma rotina útil. O checkout Xano está acoplado ao Asaas e o SQLite local não recebe pagamento real. Também faltam gestão de relatos de clientes, fidelidade vinculada aos desafios, registro de uso das peças, mala planejada e um canal persistido para solicitações de privacidade.

## Objetivo

Transformar o armário em um ciclo de recomendação, planejamento e cuidado; adicionar fidelidade baseada em desafios concluídos; substituir o Asaas pelo Mercado Pago Checkout Pro Orders; permitir relatos verdadeiros com autorização/moderação; e publicar uma política transparente sobre dados e integrações.

## Escopo

- Look do dia por clima e ocasião informados pela pessoa, com opção de salvar nos looks.
- Registro de uso de peças e cálculo opcional de custo por uso a partir do valor informado.
- Mala de viagem salva por conta, com seleção de peças do armário.
- Provador de combinações como painel visual com fotos das peças cadastradas; sem alegar prova virtual por IA.
- Solicitações de ajuste/alfaiataria persistidas e acompanháveis.
- Pontos e níveis não monetários concedidos uma única vez por desafio concluído.
- Depoimentos enviados por conta autenticada, autorização explícita, publicação somente após moderação e opção de exibição anônima.
- Página de privacidade com formulário persistido para solicitações de titulares.
- Checkout Pro Orders com preços recalculados no backend, idempotência, reserva de estoque, redirecionamento seguro e confirmação apenas após webhook assinado e consulta do recurso no Mercado Pago.
- Desativação das referências Asaas no checkout e documentação do caminho de migração.

## Fora do escopo

- Cobrança real sem credenciais de teste/produção do Mercado Pago e sem URL pública HTTPS configurada.
- Publicar depoimentos inventados ou sem consentimento.
- Prova virtual sobre corpo por IA, geração de imagens, localização GPS ou previsão do tempo externa.
- Prometer desconto, cupom ou benefício financeiro de fidelidade sem regra comercial implementada.
- Declarar conformidade legal definitiva sem revisão do responsável pelo tratamento.

## Critérios de conclusão

No modo SQLite, a pessoa consegue usar os novos fluxos autenticados e manter seus registros isolados; desafios geram pontos idempotentes; relatos aguardam aprovação; checkout demonstrativo segue sem cobrança; checkout Mercado Pago só abre com token configurado e nunca marca pedido como pago por retorno do navegador. O webhook valida assinatura, consulta a Order no Mercado Pago e confere referência e total. A política descreve o comportamento real do sistema e deixa visíveis as dependências que ainda exigem configuração externa.
