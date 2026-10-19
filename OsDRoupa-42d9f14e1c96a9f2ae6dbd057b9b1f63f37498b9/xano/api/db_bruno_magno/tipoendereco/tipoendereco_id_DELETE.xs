// Delete TIPOENDERECO record.
query "tipoendereco/{tipoendereco_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int tipoendereco_id? filters=min:1
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
    db.del TIPOENDERECO {
      field_name = "id"
      field_value = $input.tipoendereco_id
    }
  }

  response = null
  guid = "tIGQkIi9qS6ml8g8NU_da6oSWos"
}