// Get PAPEL record
query "papel/{papel_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int papel_id? filters=min:1
  }

  stack {
    db.get PAPEL {
      field_name = "id"
      field_value = $input.papel_id
    } as $papel
  
    precondition ($papel != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $papel
  guid = "B6lwA9OBt6iRk_4a9mbpY7NElUQ"
}