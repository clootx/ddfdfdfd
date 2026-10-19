// Delete STATUS_TRANSACAO record.
query "status_transacao/{status_transacao_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_transacao_id? filters=min:1
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
    db.del STATUS_TRANSACAO {
      field_name = "id"
      field_value = $input.status_transacao_id
    }
  }

  response = null
  guid = "OPkOEpORFxznY1tBM2v3Np30ocw"
}