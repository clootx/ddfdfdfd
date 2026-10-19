// Get STATUS_PEDIDO record
query "status_pedido/{status_pedido_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int status_pedido_id? filters=min:1
  }

  stack {
    db.get STATUS_PEDIDO {
      field_name = "id"
      field_value = $input.status_pedido_id
    } as $status_pedido
  
    precondition ($status_pedido != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $status_pedido
  guid = "iighgmqIe3w9N2D8JEHDjFISOTk"
}