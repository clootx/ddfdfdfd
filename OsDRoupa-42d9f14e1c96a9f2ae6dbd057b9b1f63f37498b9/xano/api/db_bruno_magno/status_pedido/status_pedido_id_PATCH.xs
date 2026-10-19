// Edit STATUS_PEDIDO record
query "status_pedido/{status_pedido_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_pedido_id? filters=min:1
    dblink {
      table = "STATUS_PEDIDO"
    }
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
    } as $CURRENT_USER

    precondition ($CURRENT_USER != null && $CURRENT_USER.role == "admin") {
      error_type = "accessdenied"
      error = "Acesso restrito à administração."
    }
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch STATUS_PEDIDO {
      field_name = "id"
      field_value = $input.status_pedido_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_pedido
  }

  response = $status_pedido
  guid = "Cxm-u0ygj1n86JY9V-pRv4Oubk8"
}