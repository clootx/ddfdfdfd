# Design — 009-wardrobe-cloud-sync

## Dados e propriedade

Nova tabela `ROUPA_CLIENTE`: `id`, `cliente_id`, `chave_local`, `nome`, `categoria`, `status`, `cor`, `estacao`, `tamanho`, `marca`, `imagem_url`, `favorita`, `created_at`. `cliente_id` sempre vem de `CLIENTE.user_id == $auth.id`; o frontend nunca escolhe o proprietário. `chave_local` terá índice único global para tornar a migração idempotente.

## APIs no grupo `PANELA_DE_BARRO`

| Método e rota | Acesso | Comportamento |
|---|---|---|
| `GET /meuArmario` | `auth=user` | Retorna somente peças do cliente autenticado |
| `POST /meuArmario` | `auth=user` | Cria uma peça ou devolve a peça existente para a mesma `chave_local`; recebe estado, cor, estação, tamanho, marca e URL HTTPS da foto |
| `PATCH /meuArmario/{item_id}` | `auth=user` | Atualiza o estado de uso permitido somente na peça da conta autenticada |
| `DELETE /meuArmario/{item_id}` | `auth=user` | Remove somente peça pertencente ao cliente autenticado |

As fontes `xano/table` e `xano/api` não mudam o workspace remoto automaticamente. Validar o schema e cada contrato antes da publicação.

## Sincronização Reflex

1. Validar sessão e ler cache local associado ao ID da conta.
2. Consultar `GET /meuArmario` com `Authorization: Bearer`.
3. Se o endpoint ainda não existir ou estiver fora do ar, exibir cache e aviso de sincronização indisponível; manter edição local para não bloquear o uso.
4. Se a leitura remota funcionar, enviar itens locais sem `chave_local` correspondente, usando ID local como chave idempotente.
5. Substituir cache pelo resultado remoto depois da sincronização. Inclusões e remoções atualizam o cache somente após confirmação Xano no modo remoto.

## Falhas

- `401/403` invalida a sessão e volta para login.
- Erro transitório mantém cache e ações locais disponíveis, com aviso explícito.
- Falha ao migrar um item não apaga a cópia local; a próxima carga tenta novamente.
- A API recusa chave local pertencente a outra conta e IDs de remoção de terceiros.
- O formulário grava categoria, estado (No armário, Em uso, Lavando ou Suja), cor, estação, tamanho, marca e URL HTTPS de uma foto; essas informações também acompanham a migração local sem substituir peças já existentes no servidor.
- O estado de uso é atualizado no Xano com autenticação e verificação do proprietário. Fotos são referências HTTPS; upload direto para o armazenamento Xano depende de configurar e validar o serviço de arquivos no workspace.

## Verificação

- Compilar Reflex e validar `/armario`.
- No Xano, validar isolamento entre contas, chave repetida, migração parcial, remoção de item alheio e recuperação após falha de rede.
