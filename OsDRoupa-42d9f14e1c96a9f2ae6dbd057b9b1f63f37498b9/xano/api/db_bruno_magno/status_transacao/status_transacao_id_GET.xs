// Get STATUS_TRANSACAO record
query "status_transacao/{status_transacao_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int status_transacao_id? filters=min:1
  }

  stack {
    db.get STATUS_TRANSACAO {
      field_name = "id"
      field_value = $input.status_transacao_id
    } as $status_transacao
  
    precondition ($status_transacao != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $status_transacao
  guid = "ut2LlJHjALUEDEnCHw-0BsSVilc"
}