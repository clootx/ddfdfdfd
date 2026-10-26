// Published in Xano workspace 147975, live branch v1. Pairing code generation
// still requires a cryptographically secure source, hashing, expiry, and atomic single use.
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
