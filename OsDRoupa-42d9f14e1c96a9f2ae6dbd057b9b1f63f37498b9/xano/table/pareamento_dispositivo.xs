// Local draft. Codes must be generated with a cryptographically secure source,
// stored as a hash, expire quickly, and be consumed atomically exactly once.
table PAREAMENTO_DISPOSITIVO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int cliente_id {
      table = "CLIENTE"
      visibility = "private"
    }
    int dispositivo_id? {
      table = "DISPOSITIVO_ARMARIO"
      visibility = "private"
    }
    text identificador filters=trim {
      visibility = "private"
    }
    text codigo_hash {
      visibility = "private"
    }
    timestamp expira_em
    timestamp? utilizado_em? {
      visibility = "private"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "codigo_hash", op: "asc"}]}
    {type: "btree", field: [{name: "cliente_id", op: "asc"}]}
    {type: "btree", field: [{name: "expira_em", op: "asc"}]}
  ]

  tags = ["modulo 12", "armario-inteligente"]
  guid = "IOT-OSD-2026-002"
}
