table FAQ {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text Pergunta? filters=trim
  
    // descrição das perguntas e respostas mais comuns do site
    // 
    text Resposta? filters=trim
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  guid = "Ogeo3Q7_sjd337NqxO3qUGMKdjw"
}