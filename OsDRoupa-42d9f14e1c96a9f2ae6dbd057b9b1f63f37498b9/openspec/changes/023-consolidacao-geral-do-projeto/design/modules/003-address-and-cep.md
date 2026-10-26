# Design Técnico — 003-address-and-cep

## Integração Reflex ↔ Xano

Os endpoints de fachada `consultaEnderecoDoCliente`, `salvaEndereco`, `atualizaEndereco` e `marcarEnderecoPadrao`, além do CRUD direto de ENDERECO no grupo `DB_BRUNO_MAGNO`, exigem `auth=user`. Cada endpoint deriva `CLIENTE` por `$auth.id`; nenhum aceita `cliente_id` como fonte de autorização. Atualização e seleção do endereço padrão carregam o registro e verificam que pertence ao cliente autenticado.

A consulta e as mutações de endereço enviam o JWT em `Authorization: Bearer <token>`. O endpoint `UpsertCEP` recebe somente os dados públicos do CEP, município e UF.

## Modelo de dados

`ENDERECO` permite múltiplos registros por cliente. Índices não únicos apoiam a listagem por cliente e endereço padrão. O servidor garante a exclusividade do endereço padrão ao desmarcar os demais do mesmo cliente.

## Limite de publicação

As fontes locais ainda precisam de validação no workspace Xano. A tabela e os endpoints em produção só mudam depois dessa validação e da migração do índice único existente.