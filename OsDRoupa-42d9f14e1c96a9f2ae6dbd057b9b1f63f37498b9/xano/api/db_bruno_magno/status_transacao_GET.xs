// Query all STATUS_TRANSACAO records
query status_transacao verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_TRANSACAO {
      return = {type: "list"}
    } as $status_transacao
  }

  response = $status_transacao
  guid = "_o6SzT2W5aiv0TQWSlAtlbVqdS8"
}