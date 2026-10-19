// Get STATUS_TTOKENIZACAO record
query "status_ttokenizacao/{status_ttokenizacao_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int status_ttokenizacao_id? filters=min:1
  }

  stack {
    db.get STATUS_TTOKENIZACAO {
      field_name = "id"
      field_value = $input.status_ttokenizacao_id
    } as $status_ttokenizacao
  
    precondition ($status_ttokenizacao != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $status_ttokenizacao
  guid = "8gv00TQMNkBSfRrWPF9uLXVXLQw"
}