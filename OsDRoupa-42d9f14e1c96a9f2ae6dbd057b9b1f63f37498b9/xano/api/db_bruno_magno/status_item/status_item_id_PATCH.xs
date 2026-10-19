// Edit STATUS_ITEM record
query "status_item/{status_item_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_item_id? filters=min:1
    dblink {
      table = "STATUS_ITEM"
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
  
    db.patch STATUS_ITEM {
      field_name = "id"
      field_value = $input.status_item_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $status_item
  }

  response = $status_item
  guid = "9ZqyqUGR2pSVzRHaYaP_HylxgVs"
}