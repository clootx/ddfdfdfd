// Query all PRODUTO records
query produto verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query PRODUTO {
      return = {type: "list"}
    } as $produto
  }

  response = $produto
  guid = "0-ON2vedh_no9d9y0h94By3gnIg"
}