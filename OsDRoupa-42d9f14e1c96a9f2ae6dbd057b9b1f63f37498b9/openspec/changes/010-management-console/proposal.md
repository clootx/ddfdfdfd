# Proposta — 010-management-console

## Contexto

O projeto já possui conta, perfil, armário, loja e base de pedidos. A próxima área necessária é uma console privada para operar catálogo, estoque, pedidos, clientes e indicadores sem expor os CRUDs públicos existentes.

## Objetivo

Criar páginas de gestão protegidas por papel de administrador e contratos Xano que validem essa permissão no servidor.

## Escopo

- `/gestao`: visão diária de pedidos, vendas, estoque e clientes.
- `/gestao/produtos`: catálogo e estoque.
- `/gestao/pedidos`: triagem e atualização do fluxo operacional.
- `/gestao/clientes`: consulta de clientes.
- `/gestao/relatorios`: indicadores agregados.
- Exigir sessão e papel `admin` em cada endpoint Xano; ocultar detalhes para conta sem permissão.

## Fora do escopo

- Usar CRUD público de tabelas comerciais.
- Atribuir papel administrativo pelo frontend.
- Alterar pedidos, estoque ou dados reais antes da publicação e validação dos contratos.

## Dependências

O schema de autenticação Xano contém papel `admin`/`member`, mas os novos endpoints administrativos ainda precisam ser publicados. As páginas devem mostrar estado de integração pendente ou acesso negado sem revelar dados.
