# Visão geral do OSDROUPA

## Arquitetura atual

- Interface em Reflex/Python, com páginas responsivas e um sistema visual compartilhado.
- Xano é o backend exigido para a entrega. Inicie com `OSDROUPA_BACKEND=xano`; SQLite continua disponível para desenvolvimento local com `OSDROUPA_BACKEND=sqlite`. Se a variável não for definida, o código atual ainda seleciona SQLite.
- OpenSpec acompanha a evolução em [`openspec/changes/README.md`](../openspec/changes/README.md).

SQLite armazena os dados em `data/osdroupa.sqlite3` ou no caminho configurado em `OSDROUPA_DB_PATH`. É indicado para desenvolvimento e uma única instância; não sincroniza entre máquinas nem substitui o Xano como backend da entrega.

## Funcionalidades no backend local

- Cadastro, login, sessões, perfil, endereços e recuperação de senha local ou por SMTP.
- Perfil com preferências opcionais de estilo, cores e tamanhos; favoritos do catálogo separados por conta no navegador.
- Catálogo, sacola, pedidos demonstrativos e checkout Mercado Pago Orders configurável por produto.
- Armário, cadastro de valor de compra, looks, agenda, recomendação contextual, mala e histórico/custo por uso.
- Oito desafios por tema, com progresso persistido; fidelidade com níveis e histórico de pontos derivados de conclusões únicas.
- Pedidos de ajuste, envio e moderação de depoimentos consentidos, política de privacidade e solicitações de titulares.
- Painel administrativo para produtos, pedidos, clientes, relatos, solicitações de privacidade e fila de alfaiataria.
- Pareamento de dispositivo apenas demonstrativo; não recebe eventos de sensores físicos.

## Pagamentos

O checkout demonstrativo não cobra. A venda real usa Mercado Pago Orders quando há credenciais configuradas no servidor. O pedido só é marcado como pago depois que o webhook assinado é validado e o backend consulta a Order diretamente. Veja [`payment-and-launch-checklist.md`](payment-and-launch-checklist.md) para configuração e pendências.

Os rascunhos XanoScript de pagamento que usavam Asaas estão bloqueados no repositório e o app impede a venda real quando usa Xano. Se os endpoints antigos já foram publicados no workspace remoto, ainda precisam ser desativados no painel. O checkout Mercado Pago está implementado no backend SQLite local; a integração correspondente ao Xano ainda precisa ser migrada, publicada e validada antes de habilitar pagamentos nesse modo.

## Limites e integrações pendentes

- Credenciais de teste/produção do Mercado Pago, segredo do webhook e origem HTTPS pública precisam ser fornecidos pelo operador; o fluxo sandbox ainda precisa ser exercitado no ambiente publicado.
- SMTP real, catálogo final com imagens e preços revisados, frete/fiscal, cancelamentos, estornos, conciliação e atendimento precisam de configuração operacional.
- Previsão do tempo automática, prova de roupa no corpo por IA e hardware IoT dependem de provedores e testes específicos. O provador atual organiza imagens das próprias peças.
- A página de privacidade e o registro de solicitações estão no produto; controlador, contato, retenção e texto final precisam ser preenchidos/revistos pelo responsável.
- Produção exige banco compartilhado, domínio HTTPS, gerenciamento de segredos, backups, restauração e validação manual com perfis de cliente e admin.

## Comandos locais

```powershell
# Modo exigido para a apresentação
$env:OSDROUPA_BACKEND = "xano"
reflex run

# Alternativa offline para desenvolvimento
$env:OSDROUPA_BACKEND = "sqlite"
reflex run
```

Para promover uma conta a admin depois de cadastrá-la:

```powershell
..\.venv\Scripts\python.exe -m OSDroupa.local_backend set-admin voce@exemplo.com
```
