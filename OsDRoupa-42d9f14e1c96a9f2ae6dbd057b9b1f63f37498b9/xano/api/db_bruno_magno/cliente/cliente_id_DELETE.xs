// Delete CLIENTE record.
query "cliente/{cliente_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int cliente_id? filters=min:1
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
    db.del CLIENTE {
      field_name = "id"
      field_value = $input.cliente_id
    }
  }

  response = null
  guid = "7YPyg6ey2tKg8rnet1b271l44Co"
}