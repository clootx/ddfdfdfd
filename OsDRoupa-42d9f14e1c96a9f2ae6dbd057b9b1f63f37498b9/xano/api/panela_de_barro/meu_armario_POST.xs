// Local draft. Validate and import in the Xano workspace before publishing.
query meuArmario verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text chave_local filters=trim
    text nome filters=trim
    text categoria filters=trim
    text? status? filters=trim
    text? cor? filters=trim
    text? estacao? filters=trim
    text? tamanho? filters=trim
    text? marca? filters=trim
    text? imagem_url? filters=trim
  }

  stack {
    precondition ($input.chave_local != "" && $input.nome != "" && $input.categoria != "") {
      error_type = "inputerror"
      error = "Informe uma chave local, nome e categoria válidos."
    }

    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }

    db.get ROUPA_CLIENTE {
      field_name = "chave_local"
      field_value = $input.chave_local
    } as $EXISTING1

    precondition ($EXISTING1 == null || $EXISTING1.cliente_id == $CLIENTE1.id) {
      error_type = "accessdenied"
      error = "A chave local já está vinculada a outra conta."
    }

    conditional {
      if ($EXISTING1 == null) {
        db.add ROUPA_CLIENTE {
          enforce_hidden_fields = false
          data = {
            cliente_id  : $CLIENTE1.id
            chave_local : $input.chave_local
            nome        : $input.nome
            categoria   : $input.categoria
            status      : $input.status|first_notempty:"No armário"
            cor         : $input.cor
            estacao     : $input.estacao
            tamanho     : $input.tamanho
            marca       : $input.marca
            imagem_url  : $input.imagem_url
            favorita    : false
          }
        } as $ROUPA1
      }
      else {
        var $ROUPA1 {
          value = $EXISTING1
        }
      }
    }
  }

  response = $ROUPA1
  guid = "WARDROBE-OSD-2026-003"
}
