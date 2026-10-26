table LOOK_CLIENTE {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int cliente_id {
      table = "CLIENTE"
    }
    text chave_local filters=trim
    text nome filters=trim
    text ocasiao filters=trim
    date? data_planejada?
    json roupa_chaves
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "chave_local", op: "asc"}]}
    {
      type : "btree"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "data_planejada", op: "asc"}
      ]
    }
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 06", "looks", "guarda-roupa"]
  guid = "LOOK-OSD-2026-001"
}
