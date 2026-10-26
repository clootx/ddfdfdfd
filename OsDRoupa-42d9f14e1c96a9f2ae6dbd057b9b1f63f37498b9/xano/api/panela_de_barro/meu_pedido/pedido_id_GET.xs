// Local draft. Validate and import in the Xano workspace before publishing.
query "meuPedido/{pedido_id}" verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int pedido_id? filters=min:1
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

    db.get PEDIDO {
      field_name = "id"
      field_value = $input.pedido_id
    } as $PEDIDO1

    precondition ($PEDIDO1 != null && $PEDIDO1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Pedido não encontrado."
    }

    db.get STATUS_PEDIDO {
      field_name = "id"
      field_value = $var.PEDIDO1.status_pedido_id
    } as $STATUSPEDIDO1

    db.query ITEM {
      where = $var.PEDIDO1.id == $db.ITEM.pedido_id
      return = {type: "list"}
      addon = [
        {name: "PRODUTO", input: {id: $output.produto_id}, as: "produto"}
      ]
    } as $ITENS1

    db.query TRANSACAO {
      where = $var.PEDIDO1.id == $db.TRANSACAO.pedido_id
      return = {type: "single"}
    } as $TRANSACAO1
  }

  response = {pedido: $PEDIDO1, status: $STATUSPEDIDO1, pagamento: $TRANSACAO1, itens: $ITENS1}
  guid = "ORDER-OSD-2026-002"
}
