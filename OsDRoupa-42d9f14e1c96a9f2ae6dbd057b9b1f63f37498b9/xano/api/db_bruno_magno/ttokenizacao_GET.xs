// Query all TTOKENIZACAO records
query ttokenizacao verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query TTOKENIZACAO {
      return = {type: "list"}
    } as $ttokenizacao
  }

  response = $ttokenizacao
  guid = "TW1_oFNfCDb2d43ZHvAlGFcgzp8"
}