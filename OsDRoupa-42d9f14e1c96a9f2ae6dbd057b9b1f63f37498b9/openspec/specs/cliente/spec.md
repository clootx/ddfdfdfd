# Especificação Consolidada — Cliente e Vínculo de Usuário

> **Origem:** Promovida a partir de [`001-foundation-identity-client`](../../changes/archive/001-foundation-identity-client/) após conclusão e validação.

## 1. Visão Geral
Define as capacidades do perfil do cliente, associação com usuário do sistema e atribuição de status operacional.

## 2. Requisitos Funcionais

### RF-CLI-01: Registro de Dados Cadastrais
O sistema deve persistir informações cadastrais do cliente:
- `nome`: texto completo (obrigatório)
- `celular`: texto formatado com DDD (obrigatório)
- `cpf`: documento identificador único
- `status_cliente_id`: chave estrangeira para `STATUS_CLIENTE`

### RF-CLI-02: Vínculo Obrigatório com Usuário
Todo cliente deve possuir o atributo `user_id` associado ao usuário que gerou o cadastro.

### RF-CLI-03: Consulta e Atualização
O cliente deve ser capaz de recuperar seus dados cadastrais através do seu token de autenticação ativo.

## 3. Cenários de Aceitação Consolidados

### Cenário: Criação de Cliente com Vínculo
- **Dado** que um usuário foi criado no sistema,
- **Quando** o endpoint `cadastra_cliente` persiste seus dados complementares,
- **Então** o registro de `CLIENTE` é criado com o campo `user_id` apontando para o usuário recém-criado e status atribuído.
