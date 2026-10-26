// Local draft. Validate and import in the Xano workspace before publishing.
query "meuArmario/{item_id}" verb=PATCH {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int item_id? filters=min:1
    text status filters=trim
  }

  stack {
    precondition (
      $input.status == "No armário" ||
      $input.status == "Em uso" ||
      $input.status == "Lavando" ||
      $input.status == "Suja"
    ) {
      error_type = "inputerror"
      error = "Estado de uso inválido."
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
      field_name = "id"
      field_value = $input.item_id
    } as $ROUPA1

    precondition ($ROUPA1 != null && $ROUPA1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Peça não encontrada."
    }

    db.patch ROUPA_CLIENTE {
      field_name = "id"
      field_value = $ROUPA1.id
      data = {status: $input.status}
    } as $ROUPA2
  }

  response = $ROUPA2
  guid = "WARDROBE-OSD-2026-005"
}
