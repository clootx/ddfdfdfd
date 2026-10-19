// Delete PRODUTO record.
query "produto/{produto_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int produto_id? filters=min:1
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
    db.del PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
    }
  }

  response = null
  guid = "aXXU6y0eflTgg_eOgMt6d9pwKfw"
}