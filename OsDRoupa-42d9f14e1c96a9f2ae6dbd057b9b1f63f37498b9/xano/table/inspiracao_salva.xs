// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
table INSPIRACAO_SALVA {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int cliente_id {
      table = "CLIENTE"
    }
    int inspiracao_id {
      table = "LOOK_INSPIRACAO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {
      type : "btree|unique"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "inspiracao_id", op: "asc"}
      ]
    }
  ]

  tags = ["change 028", "inspiracao", "feed"]
  guid = "FEED-OSD-2026-002"
}
