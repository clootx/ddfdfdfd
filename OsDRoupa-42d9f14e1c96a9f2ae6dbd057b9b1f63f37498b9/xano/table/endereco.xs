table ENDERECO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    int cliente_id? {
      table = "CLIENTE"
    }
  
    int tipoendereco_id?=1 {
      table = "TIPOENDERECO"
    }
  
    text? logradouro?=NULL filters=trim
    text numero? filters=trim
    text? complemento? filters=trim
    text bairro? filters=trim
    text? referencia? filters=trim
    bool? padrao?
    int cep_id? {
      table = "CEP"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
    {
      type : "btree"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "tipoendereco_id", op: "asc"}
      ]
    }
    {
      type : "btree"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "padrao", op: "asc"}
      ]
    }
  ]

  tags = ["modulo 01"]
  guid = "p0-s5GmJxHLRCFpiz9IUYFiq3E0"
}