// Query all PAPEL records
query papel verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query PAPEL {
      return = {type: "list"}
    } as $papel
  }

  response = $papel
  guid = "gAGxsfolw2pWDZhPEKnKc3SJq9Y"
}