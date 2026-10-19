// Add STATUS_CLIENTE record
query status_cliente verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    dblink {
      table = "STATUS_CLIENTE"
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
    db.add STATUS_CLIENTE {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $status_cliente
  }

  response = $status_cliente
  guid = "Ep5UQ29n_ZC3QN6HrDASbqMSWNs"
}