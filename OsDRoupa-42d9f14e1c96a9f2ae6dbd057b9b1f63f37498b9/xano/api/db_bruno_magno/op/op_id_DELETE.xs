// Delete OP record.
query "op/{op_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int op_id? filters=min:1
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
    db.del OP {
      field_name = "id"
      field_value = $input.op_id
    }
  }

  response = null
  guid = "CdzxjYF7GtqdbNNgucj3wPFr774"
}