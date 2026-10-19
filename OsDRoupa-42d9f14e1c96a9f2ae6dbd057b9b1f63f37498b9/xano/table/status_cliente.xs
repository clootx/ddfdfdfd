// status do cliente
table STATUS_CLIENTE {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text status_cliente? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
    {
      type : "btree|unique"
      field: [{name: "status_cliente", op: "asc"}]
    }
  ]

  tags = ["modulo 01"]
  guid = "6u3OMuKI_etWsLaHv87plSGUxBA"
}