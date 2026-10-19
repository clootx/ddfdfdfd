// Query all TIPOENDERECO records
query tipoendereco verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query TIPOENDERECO {
      return = {type: "list"}
    } as $tipoendereco
  }

  response = $tipoendereco
  guid = "iFLUcX4Csef18MyjNTdH4Pc3E_Q"
}