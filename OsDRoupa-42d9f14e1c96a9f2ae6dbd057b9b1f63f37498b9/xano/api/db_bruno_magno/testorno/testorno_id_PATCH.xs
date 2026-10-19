// Edit TESTORNO record
query "testorno/{testorno_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int testorno_id? filters=min:1
    dblink {
      table = "TESTORNO"
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
  
    db.patch TESTORNO {
      field_name = "id"
      field_value = $input.testorno_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $testorno
  }

  response = $testorno
  guid = "xvMObi62Gk3yK0aDEq-7ZA1Y6is"
}