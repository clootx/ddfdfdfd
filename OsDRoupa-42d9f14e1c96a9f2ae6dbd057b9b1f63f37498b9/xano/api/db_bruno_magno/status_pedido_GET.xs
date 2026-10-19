// Query all STATUS_PEDIDO records
query status_pedido verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_PEDIDO {
      return = {type: "list"}
    } as $status_pedido
  }

  response = $status_pedido
  guid = "3mXSwXDmm4MuR879J8LWGVGNiwY"
}