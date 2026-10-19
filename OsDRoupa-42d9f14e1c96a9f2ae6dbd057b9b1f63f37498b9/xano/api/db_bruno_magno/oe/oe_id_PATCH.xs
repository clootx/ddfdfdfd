// Edit OE record
query "oe/{oe_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int oe_id? filters=min:1
    dblink {
      table = "OE"
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
  
    db.patch OE {
      field_name = "id"
      field_value = $input.oe_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $oe
  }

  response = $oe
  guid = "9mN_BYsDhS7ZZHYLcvQMfwAm3r0"
}