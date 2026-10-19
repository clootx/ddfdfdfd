// Edit PRODUTO record
query "produto/{produto_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int produto_id? filters=min:1
    dblink {
      table = "PRODUTO"
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
  
    db.patch PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $produto
  }

  response = $produto
  guid = "6R0AubnK_JlT8pCz7Iftzt2tIPA"
}