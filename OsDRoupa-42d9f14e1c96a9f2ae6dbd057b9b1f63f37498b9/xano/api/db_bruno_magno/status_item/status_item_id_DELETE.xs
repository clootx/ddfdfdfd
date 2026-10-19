// Delete STATUS_ITEM record.
query "status_item/{status_item_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int status_item_id? filters=min:1
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
    db.del STATUS_ITEM {
      field_name = "id"
      field_value = $input.status_item_id
    }
  }

  response = null
  guid = "1YPv4qVMBSBLbivswNm6MfQh_b4"
}