# Pagamentos e pendências de lançamento

## Estado implementado

- O checkout demonstrativo continua sem cobrança e registra o pedido localmente.
- Produtos configurados como venda real usam a Orders API do Mercado Pago. O backend recalcula valores, valida endereço e estoque, cria a Order com chave idempotente e reserva o estoque.
- O pedido só passa a pago depois de um webhook Orders com assinatura válida e de uma consulta autenticada da Order ao Mercado Pago. O retorno do navegador não confirma pagamento.
- Os rascunhos XanoScript que ainda chamavam Asaas foram bloqueados no repositório. O checkout Mercado Pago está conectado ao adaptador SQLite local; o app não envia venda real ao Xano. Se os endpoints antigos já foram publicados no workspace remoto, eles precisam ser desativados também no painel Xano.
- A rota do webhook é `/api/webhooks/mercadopago` na API FastAPI do Reflex.

## Configuração necessária para cobrar em sandbox

1. Configure `MERCADOPAGO_ACCESS_TOKEN` e `MERCADOPAGO_WEBHOOK_SECRET` no ambiente do servidor. Não os coloque no código Reflex, no navegador nem em arquivos commitados.
2. Configure `OSDROUPA_PUBLIC_URL` com a origem HTTPS pública da aplicação. Localhost serve para desenvolvimento, mas não recebe notificações públicas.
3. No painel do Mercado Pago, cadastre `https://SEU-DOMINIO/api/webhooks/mercadopago` para o tópico Orders e use o segredo correspondente em `MERCADOPAGO_WEBHOOK_SECRET`.
4. Cadastre um produto de teste como **Venda real · Mercado Pago** em Gestão, use credenciais de teste e confirme o fluxo completo: redirecionamento, notificação, consulta da Order e atualização do pedido.
5. Só então configure credenciais de produção e faça uma revisão operacional de cancelamentos, estornos, atendimento e conciliação.

## O que falta no projeto

- **Credenciais e validação externa:** as credenciais do Mercado Pago, o segredo de webhook e a URL HTTPS pública precisam ser configurados. Sem isso, a integração recusa criar cobrança. O fluxo real ainda precisa ser exercitado em sandbox.
- **Backend remoto:** o Xano segue como opção para os fluxos já publicados, mas não recebeu esta implementação. As rotas de pagamento Asaas foram bloqueadas no repositório e o app bloqueia o checkout real quando `OSDROUPA_BACKEND=xano`; endpoints já publicados no workspace precisam ser desativados no painel. Para cobrar com Xano será preciso portar Orders, webhook e as novas entidades para XanoScript, importar, publicar e validar no workspace.
- **Hospedagem e banco compartilhado:** SQLite atende desenvolvimento em uma única instância. Produção multi-instância precisa de um banco servidor, migração, backups e procedimento de restauração.
- **Operação de loja:** definir frete, emissão fiscal, cancelamentos, devoluções, estornos, conciliação financeira e atendimento. O estado atual não promete esses serviços operacionais.
- **Privacidade formal:** a página e o canal de solicitações estão implementados, mas o responsável precisa informar controlador, contato, retenção e bases aplicáveis, revisar o texto e processar os pedidos recebidos.
- **Conteúdo e catálogo:** revisar imagens, preços, estoque, descrição dos produtos e textos antes de publicar. A geração de imagens depende de serviço e saldo disponíveis; a aplicação não apresenta imagens ilustrativas como fotos reais.
- **Serviços externos e hardware:** SMTP real, previsão meteorológica automática, provador corporal por IA e sensores IoT físicos ainda dependem de configuração e validação de provedores/dispositivos.
- **Validação de lançamento:** percorrer manualmente os fluxos com perfis cliente e admin no ambiente publicado, verificar isolamento por conta, permissões de gestão, pagamentos, recuperação de senha e acessibilidade/responsividade.

## Variáveis

Use os nomes listados no arquivo [`.env.example`](../.env.example). O arquivo contém apenas nomes e valores vazios; configure segredos reais no ambiente de execução.

Documentação: [criar uma Order Checkout Pro](https://www.mercadopago.com.br/developers/pt/docs/checkout-pro-orders/create-order) e [configurar Webhooks](https://www.mercadopago.com.br/developers/pt/docs/your-integrations/notifications/webhooks).
