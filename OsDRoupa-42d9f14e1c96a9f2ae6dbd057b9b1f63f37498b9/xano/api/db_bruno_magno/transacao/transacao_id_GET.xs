// Get TRANSACAO record
query "transacao/{transacao_id}" verb=GET {
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
    db.get TRANSACAO {
      field_name = "id"
      field_value = $input.transacao_id
    } as $transacao
  
    precondition ($transacao != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $transacao
  guid = "dd9RgI3Yqby9f07bxTveJfE3mjc"
}