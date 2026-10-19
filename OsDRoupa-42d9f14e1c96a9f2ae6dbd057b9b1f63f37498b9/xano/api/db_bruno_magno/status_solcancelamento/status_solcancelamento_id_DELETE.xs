// Delete STATUS_SOLCANCELAMENTO record.
query "status_solcancelamento/{status_solcancelamento_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_solcancelamento_id? filters=min:1
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
    db.del STATUS_SOLCANCELAMENTO {
      field_name = "id"
      field_value = $input.status_solcancelamento_id
    }
  }

  response = null
  guid = "xwYG1j6Qb6RTvwE8ipoZqoopQak"
}