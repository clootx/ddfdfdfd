// Query all TRANSACAO records
query transacao verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
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
    db.query TRANSACAO {
      return = {type: "list"}
    } as $transacao
  }

  response = $transacao
  guid = "39ieCaI9Y8CkzBOvSu4Xf_SkGwM"
}