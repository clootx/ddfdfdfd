table CLIENTE {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text nome? filters=trim
    text celular? filters=trim
    text data_nascimento? filters=trim
    text pronome? filters=trim
    text estilo_preferido? filters=trim
    text tamanho_superior? filters=trim
    text tamanho_inferior? filters=trim
    text tamanho_calcado? filters=trim
    text cores_favoritas? filters=trim
    text sobre_mim? filters=trim
    text cpf? filters=trim {
      visibility = "private"
    }
    int? status_cliente_id?=1 {
      table = "STATUS_CLIENTE"
    }
  
    int user_id? {
      table = "user"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "cpf", op: "asc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 01"]
  guid = "-77dpT1jAd8nZLUO1jI7NGSNoQE"
}
