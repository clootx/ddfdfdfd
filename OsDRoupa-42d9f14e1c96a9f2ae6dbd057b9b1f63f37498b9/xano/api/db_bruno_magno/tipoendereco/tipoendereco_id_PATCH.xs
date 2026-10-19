// Edit TIPOENDERECO record
query "tipoendereco/{tipoendereco_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int tipoendereco_id? filters=min:1
    dblink {
      table = "TIPOENDERECO"
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
  
    db.patch TIPOENDERECO {
      field_name = "id"
      field_value = $input.tipoendereco_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $tipoendereco
  }

  response = $tipoendereco
  guid = "KF-o15szdsX49PD-ep7fP-XUNxU"
}