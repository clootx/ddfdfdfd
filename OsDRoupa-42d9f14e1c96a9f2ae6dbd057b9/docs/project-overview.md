# Visão geral do OSDROUPA

## Arquitetura atual

- Interface em Reflex/Python, com páginas responsivas e um sistema visual compartilhado.
- Backend SQLite local como padrão. `OSDROUPA_BACKEND=xano` mantém a integração remota disponível para contratos já publicados.
- OpenSpec acompanha a evolução em [`openspec/changes/README.md`](../openspec/changes/README.md).

SQLite armazena os dados em `data/osdroupa.sqlite3` ou no caminho configurado em `OSDROUPA_DB_PATH`. É indicado para desenvolvimento e uma única instância; não sincroniza entre máquinas nem substitui um banco servidor para produção multi-instância.

## Funcionalidades no backend local

- Cadastro, login, sessões, perfil, endereços e recuperação de senha local ou por SMTP.
- Catálogo, sacola, pedidos demonstrativos e checkout Mercado Pago Orders configurável por produto.
- Armário, cadastro de valor de compra, looks, agenda, recomendação contextual, mala e histórico/custo por uso.
- Desafios com progresso persistido e pontos de fidelidade derivados de conclusões únicas.
- Pedidos de ajuste, envio e moderação de depoimentos consentidos, política de privacidade e solicitações de titulares.
- Painel administrativo para produtos, pedidos, clientes, relatos e solicitações de privacidade.
- Pareamento de dispositivo apenas demonstrativo; não recebe eventos de sensores físicos.

## Pagamentos

O checkout demonstrativo não cobra. A venda real usa Mercado Pago Orders quando há credenciais configuradas no servidor. O pedido só é marcado como pago depois que o webhook assinado é validado e o backend consulta a Order diretamente. Veja [`payment-and-launch-checklist.md`](payment-and-launch-checklist.md) para configuração e pendências.

Os rascunhos XanoScript de pagamento que usavam Asaas estão desativados. O checkout Mercado Pago foi implementado no backend SQLite local; o modo Xano ainda precisa da migração, publicação e validação desses contratos.

## Limites e integrações pendentes

- Credenciais de teste/produção do Mercado Pago, segredo do webhook e origem HTTPS pública precisam ser fornecidos pelo operador; o fluxo sandbox ainda precisa ser exercitado no ambiente publicado.
- SMTP real, catálogo final com imagens e preços revisados, frete/fiscal, cancelamentos, estornos, conciliação e atendimento precisam de configuração operacional.
- Previsão do tempo automática, prova de roupa no corpo por IA e hardware IoT dependem de provedores e testes específicos. O provador atual organiza imagens das próprias peças.
- A página de privacidade e o registro de solicitações estão no produto; controlador, contato, retenção e texto final precisam ser preenchidos/revistos pelo responsável.
- Produção exige banco compartilhado, domínio HTTPS, gerenciamento de segredos, backups, restauração e validação manual com perfis de cliente e admin.

## Comandos locais

```powershell
$env:OSDROUPA_BACKEND = "sqlite"
reflex run
```

Para promover uma conta a admin depois de cadastrá-la:

```powershell
..\.venv\Scripts\python.exe -m OSDroupa.local_backend set-admin voce@exemplo.com
```
