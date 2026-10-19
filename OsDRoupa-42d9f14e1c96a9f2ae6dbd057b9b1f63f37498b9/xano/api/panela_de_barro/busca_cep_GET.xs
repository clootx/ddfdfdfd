query buscaCEP verb=GET {
  api_group = "PANELA_DE_BARRO"

  input {
    text cep? filters=trim
  }

  stack {
    db.query CEP {
      where = $db.CEP.cep == $input.cep
      return = {type: "list"}
    } as $CEP1
  }

  response = $CEP1
  guid = "5P3P44LD4hoKVfOSmsRj8JRtwOY"
}