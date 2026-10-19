table TTOKENIZACAO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int cliente_id? {
      table = "CLIENTE"
    }
  
    text? Det_Cartao_Encript? filters=trim
    int? status_ttokenizacao_id?=1 {
      table = "STATUS_TTOKENIZACAO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 02"]
  guid = "_a1610GatXWyGYHe0xbOmrli16E"
}