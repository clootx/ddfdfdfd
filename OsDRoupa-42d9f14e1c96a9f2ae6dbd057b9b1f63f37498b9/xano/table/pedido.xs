table PEDIDO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    decimal Total?="10.2"
    text? Nfc_E? filters=trim
    text? Cod_Entrega? filters=trim
    int cliente_id? {
      table = "CLIENTE"
    }
    int? endereco_id? {
      table = "ENDERECO"
    }
    text? chave_idempotencia? filters=trim
  
    // Criado, Pedido
    int status_pedido_id?=1 {
      table = "STATUS_PEDIDO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "Nfc_E", op: "asc"}]}
    {
      type : "btree|unique"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "chave_idempotencia", op: "asc"}
      ]
    }
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 03"]
  guid = "GdX2UxZ1ZKliiTTSDRWi03itDYc"
}
