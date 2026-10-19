// Local draft. Only the authenticated device ingestion endpoint may write rows.
table EVENTO_DISPOSITIVO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int dispositivo_id {
      table = "DISPOSITIVO_ARMARIO"
      visibility = "private"
    }
    text chave_idempotencia filters=trim {
      visibility = "private"
    }
    text tipo filters=trim
    decimal? valor?
    text? unidade? filters=trim
    timestamp ocorrido_em
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {
      type : "btree|unique"
      field: [
        {name: "dispositivo_id", op: "asc"}
        {name: "chave_idempotencia", op: "asc"}
      ]
    }
    {type: "btree", field: [{name: "ocorrido_em", op: "desc"}]}
  ]

  tags = ["modulo 12", "armario-inteligente"]
  guid = "IOT-OSD-2026-003"
}
