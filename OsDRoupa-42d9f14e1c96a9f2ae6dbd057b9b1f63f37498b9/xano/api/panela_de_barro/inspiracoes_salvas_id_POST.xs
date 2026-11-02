// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
query "inspiracoesSalvas/{inspiracao_id}" verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int inspiracao_id? filters=min:1
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

    db.get LOOK_INSPIRACAO {
      field_name = "id"
      field_value = $input.inspiracao_id
    } as $INSPIRACAO1

    precondition ($INSPIRACAO1 != null && $INSPIRACAO1.status == "Publicado") {
      error_type = "notfound"
      error = "Inspiração não encontrada."
    }

    db.query INSPIRACAO_SALVA {
      where = $db.INSPIRACAO_SALVA.cliente_id == $CLIENTE1.id && $db.INSPIRACAO_SALVA.inspiracao_id == $INSPIRACAO1.id
      return = {type: "single"}
    } as $MARCA1

    conditional {
      if ($MARCA1 == null) {
        db.add INSPIRACAO_SALVA {
          data = {cliente_id: $CLIENTE1.id, inspiracao_id: $INSPIRACAO1.id}
        }
      }
    }
  }

  response = {ok: true, salvo: true}
  guid = "FEED-OSD-2026-008"
}
