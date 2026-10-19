// Get TIPOENDERECO record
query "tipoendereco/{tipoendereco_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int tipoendereco_id? filters=min:1
  }

  stack {
    db.get TIPOENDERECO {
      field_name = "id"
      field_value = $input.tipoendereco_id
    } as $tipoendereco
  
    precondition ($tipoendereco != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $tipoendereco
  guid = "BV8WY3KCLLi7XhW3tNSRPUqxSRg"
}