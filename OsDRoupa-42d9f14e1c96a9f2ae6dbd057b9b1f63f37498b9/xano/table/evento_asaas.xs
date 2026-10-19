table EVENTO_ASAAS {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }

    text event_id filters=trim
    text event_name? filters=trim
    text payment_id? filters=trim
    int? pedido_id? {
      table = "PEDIDO"
    }
    bool processed?=false
    text processing_error? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "event_id", op: "asc"}]}
    {type: "btree", field: [{name: "payment_id", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 03"]
  guid = "ASAAS-EVENT-OSD-2026-001"
}
