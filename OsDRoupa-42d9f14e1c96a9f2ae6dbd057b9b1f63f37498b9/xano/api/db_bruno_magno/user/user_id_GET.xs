// Get USER record
query "user/{user_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int user_id? filters=min:1
  }

  stack {
    db.get USER {
      field_name = "id"
      field_value = $input.user_id
    } as $user
  
    precondition ($user != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $user
  guid = "W_Cztqm10Ag0qTkid6BRQKfhmWk"
}