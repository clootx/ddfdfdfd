// Add TRANSACAO record
query transacao verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    dblink {
      table = "TRANSACAO"
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
    db.add TRANSACAO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $transacao
  }

  response = $transacao
  guid = "9B4Fd4BNmBan-XpBWkXW4xzHXRA"
}