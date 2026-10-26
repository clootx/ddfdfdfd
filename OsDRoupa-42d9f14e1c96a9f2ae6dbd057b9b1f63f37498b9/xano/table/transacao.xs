table TRANSACAO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text clienteassas? filters=trim
    text idpayment? filters=trim
    text tipo? filters=trim
    decimal valor?
    text datavenc? filters=trim
    text descricao? filters=trim
    text? status_gateway? filters=trim
    bool? pago_confirmado?=false
    timestamp? confirmado_em?
    int? pedido_id? {
      table = "PEDIDO"
    }
    int status_transacao_id? {
      table = "STATUS_TRANSACAO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "pedido_id", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  guid = "OTQyzFpCBtSKN_9NMWBgmoi82f8"
}
