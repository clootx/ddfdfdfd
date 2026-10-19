// Query all STATUS_CLIENTE records
query status_cliente verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_CLIENTE {
      return = {type: "list"}
    } as $status_cliente
  }

  response = $status_cliente
  guid = "ky7UF6OtJ4mxKA5DhaXuSuv3jwA"
}