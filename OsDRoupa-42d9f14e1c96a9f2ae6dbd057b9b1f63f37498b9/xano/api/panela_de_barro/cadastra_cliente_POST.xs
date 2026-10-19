query cadastraCliente verb=POST {
  api_group = "PANELA_DE_BARRO"

  input {
    text nome? filters=trim
    email email? filters=trim|lower
    password senha? {
      sensitive = true
      visibility = "internal"
    }
  
    text celular? filters=trim
    text cpf? filters=trim
    text status? filters=trim
  }

  stack {
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:nqm5-KuC/auth/signup"
      method = "POST"
      params = {
        name    : $input.nome
        email   : $input.email
        password: $input.senha
      }
    
      headers = ["Content-Type: application/json"]
    } as $api1
  
    // Interrompe com erro se a criação de usuário no módulo de autenticação falhar
    precondition ($var.api1.response.status == 200) {
      error_type = "accessdenied"
      error = $var.api1.response.result.message
    }
  
    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:nqm5-KuC/auth/me"
      method = "GET"
      params = `$var.api1.response.result.authToken`
      headers = [
        "Authorization: Bearer " ~ $var.api1.response.result.authToken
        "Content-Type:application/json"
      ]
    
    } as $api2
  
    db.query STATUS_CLIENTE {
      where = $input.status == $db.STATUS_CLIENTE.status_cliente
      return = {type: "list"}
    } as $STATUS_CLIENTE1
  
    db.add CLIENTE {
      enforce_hidden_fields = false
      data = {
        created_at       : "now"
        nome             : $input.nome
        celular          : $input.celular
        cpf              : $input.cpf
        status_cliente_id: $var.STATUS_CLIENTE1[0].id
        user_id          : `$var.api2.response.result.id`
      }
    } as $CLIENTE1
  }

  response = {
    user     : $api2.response.result
    cliente  : $CLIENTE1
    authToken: $api1.response.result.authToken
  }

  guid = "cjM5UwXp3r_c0Lcp6vEaqtOUdJ0"
}