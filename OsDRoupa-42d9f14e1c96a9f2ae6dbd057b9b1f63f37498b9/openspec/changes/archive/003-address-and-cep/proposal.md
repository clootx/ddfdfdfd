# Proposta — 003-address-and-cep

## Contexto
A gestão de endereços é necessária para perfil e checkout. Os wrappers Xano anteriores aceitavam `cliente_id` do navegador e não validavam propriedade; o schema também limitava cada cliente a um endereço do mesmo tipo.

## Objetivo
Permitir consulta, cadastro e atualização de endereços com CEP, vinculando cada operação ao cliente resolvido pela sessão Xano.

## Escopo incluído
- Consulta e preenchimento por CEP.
- Lista, criação, atualização e seleção de endereço padrão.
- Verificação de propriedade no servidor para leitura e mutações.
- Suporte a múltiplos endereços por cliente.
- Envio do JWT somente no cabeçalho Bearer.

## Fora do escopo
- Publicação ou migração em workspace Xano nesta etapa local.
- Cotação de frete e cálculo de prazo.

## Dependências
A validação final depende de importar os rascunhos no Xano e exercitar duas contas de teste.