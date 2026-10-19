// Get PRODUTO record
query "produto/{produto_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int produto_id? filters=min:1
  }

  stack {
    db.get PRODUTO {
      field_name = "id"
      field_value = $input.produto_id
    } as $produto
  
    precondition ($produto != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $produto
  guid = "MUc1u5DYRSoJa5p4ldY15MbqjM8"
}