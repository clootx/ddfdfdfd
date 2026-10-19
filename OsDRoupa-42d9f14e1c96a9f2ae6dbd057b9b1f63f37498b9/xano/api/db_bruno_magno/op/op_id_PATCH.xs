// Edit OP record
query "op/{op_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int op_id? filters=min:1
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
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch OP {
      field_name = "id"
      field_value = $input.op_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $op
  }

  response = $op
  guid = "ALUq5pkH4I9o0Bp5UIlQqED4Tpc"
}