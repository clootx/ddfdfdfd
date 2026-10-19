// Add TIPOENDERECO record
query tipoendereco verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    dblink {
      table = "TIPOENDERECO"
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
    db.add TIPOENDERECO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $tipoendereco
  }

  response = $tipoendereco
  guid = "kGBCPBLwqICCP-dmw670LHymR7Y"
}