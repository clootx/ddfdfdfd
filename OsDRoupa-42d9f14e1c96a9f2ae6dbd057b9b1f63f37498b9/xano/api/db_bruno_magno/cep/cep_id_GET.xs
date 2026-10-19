// Get CEP record
query "cep/{cep_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int cep_id? filters=min:1
  }

  stack {
    db.get CEP {
      field_name = "id"
      field_value = $input.cep_id
    } as $cep
  
    precondition ($cep != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $cep
  guid = "1RGC2nHo7wIidT68V4muCzr57KE"
}