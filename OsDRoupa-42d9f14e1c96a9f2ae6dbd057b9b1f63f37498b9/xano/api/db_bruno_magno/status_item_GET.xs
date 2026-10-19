// Query all STATUS_ITEM records
query status_item verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_ITEM {
      return = {type: "list"}
    } as $status_item
  }

  response = $status_item
  guid = "psaO9dbUjozCg0DJD9QWYVR9oOI"
}