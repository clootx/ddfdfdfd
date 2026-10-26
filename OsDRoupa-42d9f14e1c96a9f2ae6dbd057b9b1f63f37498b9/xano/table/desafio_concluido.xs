table DESAFIO_CONCLUIDO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int user_id {
      table = "user"
      visibility = "private"
    }
    text desafio_id filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {
      type : "btree|unique"
      field: [
        {name: "user_id", op: "asc"}
        {name: "desafio_id", op: "asc"}
      ]
    }
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 11", "desafios"]
  guid = "CONTENT-OSD-2026-001"
}
