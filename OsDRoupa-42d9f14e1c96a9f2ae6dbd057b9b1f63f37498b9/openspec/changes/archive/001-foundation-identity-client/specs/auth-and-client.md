# Especificação Arquivada — Autenticação e Perfil de Cliente

## Requisitos Funcionais Implementados

### RF-01 — Autenticação de Usuário
O sistema permite cadastro e autenticação de usuários via e-mail e senha, com unicidade de e-mail e requisitos de senha (mínimo 8 caracteres, maiúscula, número).

### RF-02 — Vínculo de Conta/Organização
Usuários e clientes operam sob um contexto de `account` para segmentação organizacional.

### RF-03 — Cadastro de Cliente
Usuários autenticados criam seu perfil de cliente contendo nome, celular, CPF e status inicial.

### RF-04 — Vínculo Usuário-Cliente
O registro na tabela `CLIENTE` mantém a referência `user_id` apontando para o registro na tabela `user`.

### RF-05 — Consulta e Atualização do Perfil
O cliente autenticado consulta seus dados e mantém suas informações atualizadas.

### RF-06 — Status do Cliente
O cliente possui status atribuído a partir de `STATUS_CLIENTE`.

---

## Cenários de Aceitação Validados

### Cenário 1: Cadastro de novo usuário
- **Dado** que um visitante preenche nome, e-mail e senha válida,
- **Quando** submete o cadastro,
- **Então** o sistema cria o usuário e retorna token de autenticação.

### Cenário 2: Login com credenciais válidas
- **Dado** usuário cadastrado,
- **Quando** informa e-mail e senha corretos,
- **Então** o sistema autentica com sucesso e estabelece a sessão.

### Cenário 3: Criação de perfil vinculando usuário
- **Dado** usuário autenticado,
- **Quando** cadastra seus dados de cliente,
- **Então** o registro é salvo com `user_id` e status ativo no banco.
