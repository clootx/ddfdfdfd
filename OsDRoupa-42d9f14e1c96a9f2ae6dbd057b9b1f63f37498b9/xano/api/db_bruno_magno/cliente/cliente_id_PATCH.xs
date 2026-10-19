// Edit CLIENTE record
query "cliente/{cliente_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int cliente_id? filters=min:1
    dblink {
      table = "CLIENTE"
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
  
    db.patch CLIENTE {
      field_name = "id"
      field_value = $input.cliente_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $cliente
  }

  response = $cliente
  guid = "fq2jRJqV0ir4muueMFugEe73g7w"
}