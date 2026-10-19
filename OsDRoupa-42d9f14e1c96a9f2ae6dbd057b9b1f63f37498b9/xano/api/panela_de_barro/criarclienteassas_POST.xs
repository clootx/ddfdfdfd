query criarclienteassas verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text authtoken? filters=trim
  }

  stack {
    // Deprecated: replaces the old caller-supplied auth token flow.
    precondition (1 == 0) {
      error_type = "accessdenied"
      error = "Esta integração legada foi desativada."
    }

    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:6LtoY7Zt/buscaCliente"
      method = "GET"
      params = {authtoken: $input.authtoken}
    } as $api1
  
    conditional {
      if (`$var.api1.response.status` == 200) {
        db.get user {
          field_name = "id"
          field_value = `$var.api1.response.result.cliente.user_id`
        } as $user1
      
        db.get "" {
          field_name = "Plataforma"
          field_value = "Asaas"
        } as $tokens1
      
        api.request {
          url = "https://api-sandbox.asaas.com/v3/customers"
          method = "POST"
          params = {
            name   : $user1.name
            cpfCnpj: $api1.response.result.cliente.cpf
          }
        
          headers = []
            |push:"User-Agent: XanoApp/1.0 (contact: bruno.magno@aluno.impacta.edu.br)"
            |push:"Accept: application/json"
            |push:$tokens1.token
            |push:"Content-Type: application/json"
        } as $api2
      
        var $codigoclienteassas {
          value = `$var.api2.response.result.id`
        }
      
        db.get STATUS_TTOKENIZACAO {
          field_name = "status"
          field_value = `"Criada"`
        } as $STATUS_TTOKENIZACAO1
      
        db.add TTOKENIZACAO {
          enforce_hidden_fields = false
          data = {
            created_at            : "now"
            cliente_id            : `$var.api1.response.result.cliente.id`
            det_cartao_encript    : ""
            status_ttokenizacao_id: `$var.STATUS_TTOKENIZACAO1.id`
          }
        } as $TTOKENIZACAO1
      
        db.add CARTAOTOKNZD {
          enforce_hidden_fields = false
          data = {
            created_at        : "now"
            cliente_id        : `$var.api1.response.result.cliente.id`
            token             : ""
            codigoclienteassas: `$var.codigoclienteassas`
          }
        } as $CARTAOTOKNZD1
      
        var $status {
          value = {status: true, mensagem: "Cliente cadastrado no Asaas."}
        }
      }
    
      else {
        var $status {
          value = {
            status  : false
            mensagem: "Cliente não pôde ser cadastrado no Asaas."
          }
        }
      }
    }
  }

  response = {status: $status}
  guid = "UvQq-EKM5l_M2aa4T-7gdvXS1NI"
}
