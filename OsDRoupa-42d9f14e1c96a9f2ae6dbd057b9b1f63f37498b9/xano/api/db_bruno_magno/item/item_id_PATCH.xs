// Edit ITEM record
query "item/{item_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int item_id? filters=min:1
    dblink {
      table = "ITEM"
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
  
    db.patch ITEM {
      field_name = "id"
      field_value = $input.item_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $item
  }

  response = $item
  guid = "yp0jv8Ei1WfnMOa1kMfMiByw9fw"
}