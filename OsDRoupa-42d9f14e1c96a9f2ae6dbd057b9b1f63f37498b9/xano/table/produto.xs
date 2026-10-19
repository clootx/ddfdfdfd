table PRODUTO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text Nome? filters=trim
    text Descricao? filters=trim
    text Categoria? filters=trim
    int Qtd_Disp? filters=min:0
    text Url_Imagem? filters=trim
    decimal Preco?="10.2"
    bool Precisa_Produzir?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "Nome", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 03"]
  guid = "-VDyy2Cnyi3QlgiPLuHeI5UNk1k"
}
