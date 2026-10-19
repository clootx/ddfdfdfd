// Query all CARTAOTOKNZD records
query cartaotoknzd verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query CARTAOTOKNZD {
      return = {type: "list"}
    } as $cartaotoknzd
  }

  response = $cartaotoknzd
  guid = "8yN9QX8g0NMaP4odpF3daxQylSA"
}