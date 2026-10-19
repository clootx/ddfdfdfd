// Delete STATUS_CLIENTE record.
query "status_cliente/{status_cliente_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_cliente_id? filters=min:1
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
    db.del STATUS_CLIENTE {
      field_name = "id"
      field_value = $input.status_cliente_id
    }
  }

  response = null
  guid = "k5Vz5rCHqbyAcqgIIgssi7KKKZk"
}