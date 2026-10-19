// Query all CEP records
query cep verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query CEP {
      return = {type: "list"}
    } as $cep
  }

  response = $cep
  guid = "NRUmoI_BiPv7S41WwVBWAyGw_gA"
}