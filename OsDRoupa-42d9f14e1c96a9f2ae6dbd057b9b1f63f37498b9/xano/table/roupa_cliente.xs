table ROUPA_CLIENTE {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int cliente_id {
      table = "CLIENTE"
    }
    text chave_local filters=trim
    text nome filters=trim
    text categoria filters=trim
    text status?="No armário" filters=trim
    text? cor? filters=trim
    text? estacao? filters=trim
    text? tamanho? filters=trim
    text? marca? filters=trim
    text? imagem_url? filters=trim
    bool? favorita?=false
    timestamp? ultimo_uso?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "chave_local", op: "asc"}]}
    {
      type : "btree"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "categoria", op: "asc"}
      ]
    }
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 06", "guarda-roupa"]
  guid = "WARDROBE-OSD-2026-001"
}
