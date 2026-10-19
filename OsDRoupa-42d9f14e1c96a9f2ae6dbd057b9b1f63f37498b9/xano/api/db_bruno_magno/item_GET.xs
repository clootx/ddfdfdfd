// Query all ITEM records
query item verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
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
    db.query ITEM {
      return = {type: "list"}
    } as $item
  }

  response = $item
  guid = "hVmW2t1QTE-xKKI9-eMTGfg0e_s"
}