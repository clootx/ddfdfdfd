// Edit STATUS_TRANSACAO record
query "status_transacao/{status_transacao_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_transacao_id? filters=min:1
    dblink {
      table = "STATUS_TRANSACAO"
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
  
    db.patch STATUS_TRANSACAO {
      field_name = "id"
      field_value = $input.status_transacao_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_transacao
  }

  response = $status_transacao
  guid = "8gmWkZPLJnyi5X-aK9IsM0Ky2XU"
}