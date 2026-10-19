// Delete CARTAOTOKNZD record.
query "cartaotoknzd/{cartaotoknzd_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int cartaotoknzd_id? filters=min:1
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
    db.del CARTAOTOKNZD {
      field_name = "id"
      field_value = $input.cartaotoknzd_id
    }
  }

  response = null
  guid = "AzSAsy8hysjYnI04wxPZwQORPh8"
}