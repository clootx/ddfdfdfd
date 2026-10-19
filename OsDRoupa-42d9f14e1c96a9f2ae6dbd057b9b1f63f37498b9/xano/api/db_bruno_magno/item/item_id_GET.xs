// Get ITEM record
query "item/{item_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int item_id? filters=min:1
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
    db.get ITEM {
      field_name = "id"
      field_value = $input.item_id
    } as $item
  
    precondition ($item != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $item
  guid = "8OVYPt9i6qBzRY1k9BzeEtWVg5A"
}