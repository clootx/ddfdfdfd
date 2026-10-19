# Especificação — Console de gestão

## RF-MGMT-01: Acesso administrativo

Somente conta com papel `admin` pode consultar os módulos de gestão; cada chamada valida o papel no Xano.

### Cenário: conta comum
- **Dado** que a pessoa autenticada tem papel `member`
- **Quando** acessa uma página ou endpoint de gestão
- **Então** não recebe indicadores, catálogo interno ou dados de clientes

## RF-MGMT-02: Operação

Admin pode consultar catálogo, estoque e fila de pedidos. Alterações de estado são validadas no servidor e não modificam valor financeiro.

## RF-MGMT-03: Clientes e relatórios

Listagens de clientes e relatórios são paginadas/agregadas e acessíveis somente a admin.

## RF-MGMT-04: Integração indisponível

Quando uma API ainda não estiver publicada, a interface informa o estado pendente e não simula alterações.
