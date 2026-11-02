// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
query "inspiracoesSalvas/{inspiracao_id}" verb=DELETE {
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

    db.query INSPIRACAO_SALVA {
      where = $db.INSPIRACAO_SALVA.cliente_id == $CLIENTE1.id && $db.INSPIRACAO_SALVA.inspiracao_id == $input.inspiracao_id
      return = {type: "single"}
    } as $MARCA1

    conditional {
      if ($MARCA1 != null) {
        db.del INSPIRACAO_SALVA {
          field_name = "id"
          field_value = $MARCA1.id
        }
      }
    }
  }

  response = {ok: true, salvo: false}
  guid = "FEED-OSD-2026-009"
}
