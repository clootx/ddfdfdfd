// Delete TRANSACAO record.
query "transacao/{transacao_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int transacao_id? filters=min:1
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
    db.del TRANSACAO {
      field_name = "id"
      field_value = $input.transacao_id
    }
  }

  response = null
  guid = "pMa3VlYClsQHci3-2RSIIwoNmW4"
}