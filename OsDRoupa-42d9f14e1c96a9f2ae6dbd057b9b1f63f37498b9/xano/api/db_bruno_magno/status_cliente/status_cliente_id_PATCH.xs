// Edit STATUS_CLIENTE record
query "status_cliente/{status_cliente_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_cliente_id? filters=min:1
    dblink {
      table = "STATUS_CLIENTE"
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
  
    db.patch STATUS_CLIENTE {
      field_name = "id"
      field_value = $input.status_cliente_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_cliente
  }

  response = $status_cliente
  guid = "X0n-z59et0Oi7jCdvbdiW29BN6k"
}