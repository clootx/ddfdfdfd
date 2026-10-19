// Local draft. Validate and import in the Xano workspace before publishing.
query "meuArmario/{item_id}" verb=DELETE {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int item_id? filters=min:1
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

    db.get ROUPA_CLIENTE {
      field_name = "id"
      field_value = $input.item_id
    } as $ROUPA1

    precondition ($ROUPA1 != null && $ROUPA1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Peça não encontrada."
    }

    db.del ROUPA_CLIENTE {
      field_name = "id"
      field_value = $ROUPA1.id
    }
  }

  response = {deleted: true}
  guid = "WARDROBE-OSD-2026-004"
}
