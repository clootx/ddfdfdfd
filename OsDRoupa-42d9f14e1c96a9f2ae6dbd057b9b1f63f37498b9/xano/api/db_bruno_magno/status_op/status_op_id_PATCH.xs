// Edit STATUS_OP record
query "status_op/{status_op_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_op_id? filters=min:1
    dblink {
      table = "STATUS_OP"
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
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch STATUS_OP {
      field_name = "id"
      field_value = $input.status_op_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_op
  }

  response = $status_op
  guid = "o2xks1nkn8fHqmWn1A-mBALlRxg"
}