// Edit PEDIDO record
query "pedido/{pedido_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int pedido_id? filters=min:1
    dblink {
      table = "PEDIDO"
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
  
    db.patch PEDIDO {
      field_name = "id"
      field_value = $input.pedido_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $pedido
  }

  response = $pedido
  guid = "mQbOHAQ6AbrMZ-e56K3R-ggVMAI"
}