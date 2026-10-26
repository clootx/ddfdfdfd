# Proposta: backend local persistente para completar os fluxos

## Problema

Várias rotas Reflex já existem, mas dependem de APIs e credenciais externas para autenticação, endereço, catálogo, pedidos, armário, looks, desafios e gestão. A instância Xano Free não disponibiliza sandbox/prévia e o projeto não possui configuração funcional de Asaas ou envio de e-mail neste ambiente.

## Objetivo

Adicionar um backend local em SQLite como opção padrão de desenvolvimento, preservando a integração Xano como modo explícito. Persistir os dados de usuário e os fluxos do produto com autorização e propriedade verificadas no servidor, e completar a interface administrativa necessária para operar o catálogo e pedidos demonstrativos.

## Escopo incluído

- Persistência SQLite com caminho configurável e inicialização idempotente.
- Cadastro/login local com hash de senha, sessão expirada e isolamento por usuário.
- Endereços, catálogo demonstrativo de moda, armário, looks, desafios e pedidos sem cobrança.
- Gestão protegida por papel admin, com cadastro de produto e transições válidas de pedido.
- Experiência local explicitamente demonstrativa para pareamento de dispositivo.
- Configuração/documentação para manter Xano como modo alternativo.
- Páginas de perfil editável e recuperação de senha, com envio de e-mail habilitado apenas quando SMTP estiver configurado.

## Fora do escopo

- Declarar um pedido demonstrativo como pago ou simular aprovação de cobrança.
- Substituir gateway Asaas, entrega de e-mail ou autenticação de hardware por respostas falsas.
- Usar SQLite como banco multi-instância de produção ou publicar alterações em serviços externos.
- Alterar ou migrar dados já armazenados no Xano sem exportação e revisão explícitas.

## Critérios de conclusão

Uma conta criada localmente consegue entrar, editar perfil, manter endereços e dados do armário/look entre sessões, navegar em um catálogo de moda, concluir um pedido demonstrativo, consultar o pedido e acessar as páginas de gestão somente com papel admin. Operações de pedido e pagamento permanecem claramente separadas.
