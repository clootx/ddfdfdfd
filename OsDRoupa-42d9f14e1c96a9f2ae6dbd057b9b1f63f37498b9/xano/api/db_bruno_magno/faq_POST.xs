// Add FAQ record
query faq verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    dblink {
      table = "FAQ"
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
    db.add FAQ {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $faq
  }

  response = $faq
  guid = "DD-Z-LIXb7B_J094Kr5VDTYxFh8"
}