// Local draft. Validate and import in the Xano workspace before publishing.
query meusLooks verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text chave_local filters=trim
    text nome filters=trim
    text ocasiao filters=trim
    date? data_planejada?
    text[] roupa_chaves filters=max:10
  }

  stack {
    precondition ($input.chave_local != "" && $input.nome != "" && $input.ocasiao != "") {
      error_type = "inputerror"
      error = "Informe a chave, o nome e a ocasião do look."
    }

    precondition (($input.roupa_chaves|count) > 0) {
      error_type = "inputerror"
      error = "Escolha pelo menos uma peça."
    }

    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }

    db.query ROUPA_CLIENTE {
      where = $CLIENTE1.id == $db.ROUPA_CLIENTE.cliente_id && $db.ROUPA_CLIENTE.chave_local in $input.roupa_chaves
      return = {type: "list"}
    } as $ROUPAS1

    precondition (($ROUPAS1|count) == ($input.roupa_chaves|count)) {
      error_type = "accessdenied"
      error = "Uma ou mais peças não pertencem a esta conta."
    }

    db.get LOOK_CLIENTE {
      field_name = "chave_local"
      field_value = $input.chave_local
    } as $EXISTING1

    precondition ($EXISTING1 == null || $EXISTING1.cliente_id == $CLIENTE1.id) {
      error_type = "accessdenied"
      error = "A chave local já está vinculada a outra conta."
    }

    precondition (
      $EXISTING1 == null ||
      ($EXISTING1.nome == $input.nome && $EXISTING1.ocasiao == $input.ocasiao &&
      $EXISTING1.data_planejada == $input.data_planejada &&
      $EXISTING1.roupa_chaves == $input.roupa_chaves)
    ) {
      error_type = "inputerror"
      error = "A chave local já foi usada com outros dados."
    }

    conditional {
      if ($EXISTING1 == null) {
        db.add LOOK_CLIENTE {
          enforce_hidden_fields = false
          data = {
            cliente_id      : $CLIENTE1.id
            chave_local     : $input.chave_local
            nome            : $input.nome
            ocasiao         : $input.ocasiao
            data_planejada  : $input.data_planejada
            roupa_chaves    : $input.roupa_chaves
          }
        } as $LOOK1
      }
      else {
        var $LOOK1 {
          value = $EXISTING1
        }
      }
    }
  }

  response = {look: $LOOK1}
  guid = "LOOK-OSD-2026-003"
}
