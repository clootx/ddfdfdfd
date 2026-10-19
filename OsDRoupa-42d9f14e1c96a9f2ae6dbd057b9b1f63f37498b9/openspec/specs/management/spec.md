# Especificação consolidada — Console de Gestão

## RF-MGMT-01: Autorização

Somente conta `admin` pode consultar dados administrativos. Cada endpoint verifica o papel no Xano; a interface nunca concede acesso.

Escritas CRUD genéricas de produto, cliente, pedido, item, transação e status exigem papel administrativo. Leituras genéricas de dados de cliente, pedido, item e transação também são administrativas. O catálogo de produto continua público; demais consultas públicas ficam limitadas a dados de referência não sensíveis.

## RF-MGMT-02: Operação

Admin pode consultar catálogo, estoque e fila de pedidos. Mudanças de estado devem ser permitidas pelo servidor e não alteram o total financeiro.

## RF-MGMT-03: Clientes e relatórios

Consultas de clientes e relatórios são administrativas e retornam apenas os campos necessários.

## RF-MGMT-04: Falhas

Integração indisponível informa pendência; acesso negado não apresenta dados e falha de rede não simula atualização.
