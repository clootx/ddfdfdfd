# Design — 021-experiencia-cliente-completa

## Arquitetura

O frontend continua em Reflex. O backend SQLite mantém o contrato autenticado `perfil`, `buscaCliente`, `fidelidade` e `concluirDesafio`. A migração de perfil é aditiva e idempotente. O XanoScript recebe o esboço de campos equivalente, mas só passa a funcionar remotamente depois de importação, ajuste do schema e publicação pelo operador.

Favoritos são preferências de navegação não sensíveis mantidas em LocalStorage sob uma chave por identificador da conta. O catálogo continua sendo carregado do endpoint de produtos; favoritos não autorizam nem alteram estoque, preço ou compra.

## Perfil

O SQLite persiste nome, celular, data de nascimento opcional, pronome, estilo preferido, tamanhos de parte superior/inferior/calçado, cores favoritas e nota curta. E-mail continua somente leitura porque é identificador de login. A validação de propriedade usa a sessão autenticada, com limites de tamanho e data não futura.

## Desafios e fidelidade

O catálogo de desafios possui IDs estáveis e pontos definidos no servidor. Conclusões permanecem únicas por conta e desafio. A tela filtra por tema e estado, oferece acesso à atividade correspondente e registra que a conclusão é autodeclarada. Pontos, nível atual, próximo marco, percentual e histórico são calculados com base nas conclusões salvas; não existe resgate financeiro.

## Loja e checkout

O usuário pode favoritar e filtrar produtos. A lista é local ao navegador e separada pelo ID de conta. Checkout mostra uma estimativa de subtotal derivada apenas para visualização; o backend recalcula preço, disponibilidade, estoque e total. Frete e prazo não são inventados.

Para venda real, o backend cria a Order Mercado Pago e retorna um link HTTPS. A pessoa escolhe entre os meios que o vendedor habilitou no checkout hospedado. O OSDROUPA não recebe cartão; só o webhook validado confirma pagamento. O fluxo de demonstração continua sem cobrança.

## Responsividade e estados

Campos, filtros, cards e etapas refluem de uma coluna em telas estreitas para grades em telas maiores. Mensagens de carregamento, erro, lista vazia, pedido demonstrativo e pagamento pendente mantêm linguagem distinta.
