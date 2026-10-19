// Edit STATUS_OE record
query "status_oe/{status_oe_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_oe_id? filters=min:1
    dblink {
      table = "STATUS_OE"
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
  
    db.patch STATUS_OE {
      field_name = "id"
      field_value = $input.status_oe_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_oe
  }

  response = $status_oe
  guid = "u8KQ3sVnYNmR8wC7hiYnsKwgKpA"
}