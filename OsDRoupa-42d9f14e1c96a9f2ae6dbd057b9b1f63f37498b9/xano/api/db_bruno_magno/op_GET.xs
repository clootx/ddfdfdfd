// Query all OP records
query op verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query OP {
      return = {type: "list"}
    } as $op
  }

  response = $op
  guid = "UnTRQyRKOlkhfWaV2a3BAqVPRio"
}