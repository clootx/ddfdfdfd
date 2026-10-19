query consultaEnderecoDoCliente verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }
  
    db.query ENDERECO {
      where = $var.CLIENTE1.id == $db.ENDERECO.cliente_id
      return = {type: "list"}
      output = [
        "id"
        "created_at"
        "cliente_id"
        "logradouro"
        "numero"
        "complemento"
        "bairro"
        "referencia"
        "padrao"
      ]
    
      addon = [
        {name: "CEP", input: {CEP_id: $output.cep_id}, as: "_cep"}
      ]
    } as $ENDERECO1
  }

  response = {endereco1: $ENDERECO1}
  guid = "S-72DHFsqnnsCYk_NfsdGp-p7XQ"
}
