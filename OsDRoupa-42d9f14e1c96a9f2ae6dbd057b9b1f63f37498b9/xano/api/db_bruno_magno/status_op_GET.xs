// Query all STATUS_OP records
query status_op verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_OP {
      return = {type: "list"}
    } as $status_op
  }

  response = $status_op
  guid = "jPchNR2Fa_9npU30SgA2sRAwBUI"
}