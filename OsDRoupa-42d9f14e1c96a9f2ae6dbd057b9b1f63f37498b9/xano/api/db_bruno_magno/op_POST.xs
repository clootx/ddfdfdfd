// Add OP record
query op verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    dblink {
      table = "OP"
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
    db.add OP {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $op
  }

  response = $op
  guid = "29vucHIpsMfgDbwKZvYX1mEGCUg"
}