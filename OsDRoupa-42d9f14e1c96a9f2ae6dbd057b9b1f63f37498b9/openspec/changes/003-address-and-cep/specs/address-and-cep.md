# Especificação — Gestão de Endereços e Integração de CEP

## RF-END-01: Consulta e preenchimento de CEP
A aplicação valida CEP com oito dígitos e preenche logradouro, bairro, cidade e UF quando o serviço público retorna dados.

### Cenário: CEP válido
- **Dado** que a pessoa informa um CEP com oito dígitos
- **Quando** a consulta encontra o CEP
- **Então** os campos de endereço são preenchidos com a resposta do serviço

## RF-END-02: Múltiplos endereços por cliente
Uma conta pode cadastrar mais de um endereço, cada um vinculado ao cliente derivado da sessão autenticada.

### Cenário: cadastrar endereço adicional
- **Dado** que há uma sessão válida e um endereço existente
- **Quando** a pessoa salva outro endereço
- **Então** o Xano cria outro registro associado ao mesmo cliente

## RF-END-03: Isolamento entre clientes
Listagem, criação, atualização e seleção do padrão usam o cliente da sessão. O frontend não define a identidade do proprietário.

### Cenário: tentar alterar endereço de outra conta
- **Dado** que o endereço não pertence ao usuário autenticado
- **Quando** a conta envia atualização ou seleção de padrão para esse ID
- **Então** o Xano responde não encontrado ou acesso negado sem alterar o registro

## RF-END-04: Endereço padrão exclusivo
Cada cliente pode ter no máximo um endereço padrão. Ao marcar outro, os demais endereços desse mesmo cliente deixam de ser padrão.

### Cenário: trocar endereço padrão
- **Dado** que existe um endereço padrão
- **Quando** a pessoa marca outro endereço como padrão
- **Então** somente o novo endereço fica marcado como padrão para esse cliente

## RF-END-05: Token em cabeçalho
O JWT é enviado somente em `Authorization: Bearer <token>`, nunca em query string.