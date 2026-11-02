// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
query "minhasInspiracoes/{inspiracao_id}" verb=DELETE {
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

    precondition ($INSPIRACAO1 != null && $INSPIRACAO1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Inspiração não encontrada."
    }

    db.query INSPIRACAO_SALVA {
      where = $db.INSPIRACAO_SALVA.inspiracao_id == $INSPIRACAO1.id
      return = {type: "list"}
    } as $MARCAS1

    foreach ($MARCAS1) {
      each as $MARCA {
        db.del INSPIRACAO_SALVA {
          field_name = "id"
          field_value = $MARCA.id
        }
      }
    }

    db.del LOOK_INSPIRACAO {
      field_name = "id"
      field_value = $INSPIRACAO1.id
    }
  }

  response = {deleted: true}
  guid = "FEED-OSD-2026-006"
}
