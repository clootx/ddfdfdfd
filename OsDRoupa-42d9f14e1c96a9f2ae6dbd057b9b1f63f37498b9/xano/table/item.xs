table ITEM {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int pedido_id? {
      table = "PEDIDO"
    }
  
    int Qtd? filters=min:1
    decimal Valor_Unit?="10.2"
    decimal Subtotal?="10.2"
    int produto_id? {
      table = "PRODUTO"
    }
  
    int status_item_id? {
      table = "STATUS_ITEM"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {
      type : "btree|unique"
      field: [
        {name: "pedido_id", op: "asc"}
        {name: "produto_id", op: "asc"}
      ]
    }
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 03"]
  guid = "euGUxkENI-jpn0P9IIK07Xp9Sys"
}