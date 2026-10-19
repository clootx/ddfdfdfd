// Local draft. Validate and import in the Xano workspace before publishing.
query meusPedidos verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }

    db.query PEDIDO {
      where = $var.CLIENTE1.id == $db.PEDIDO.cliente_id
      return = {type: "list"}
      sort = {PEDIDO.created_at: "desc"}
      addon = [
        {name: "STATUS_PEDIDO", input: {status_pedido_id: $output.status_pedido_id}, as: "status"}
      ]
    } as $PEDIDOS1
  }

  response = {pedidos: $PEDIDOS1}
  guid = "ORDERS-OSD-2026-001"
}
