// Get STATUS_CLIENTE record
query "status_cliente/{status_cliente_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int status_cliente_id? filters=min:1
  }

  stack {
    db.get STATUS_CLIENTE {
      field_name = "id"
      field_value = $input.status_cliente_id
    } as $status_cliente
  
    precondition ($status_cliente != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $status_cliente
  guid = "f6X3vxtsEStq5_A_tEh_hQpTywI"
}