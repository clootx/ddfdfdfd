// Add STATUS_ITEM record
query status_item verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
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
    db.add STATUS_ITEM {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $status_item
  }

  response = $status_item
  guid = "D9hTGHBe5sntzFoPoFMq1o01cxU"
}