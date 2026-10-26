// Local draft. Validate and import in the Xano workspace before publishing.
query "meusLooks/{look_id}" verb=DELETE {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int look_id? filters=min:1
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

    db.get LOOK_CLIENTE {
      field_name = "id"
      field_value = $input.look_id
    } as $LOOK1

    precondition ($LOOK1 != null && $LOOK1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Look não encontrado."
    }

    db.del LOOK_CLIENTE {
      field_name = "id"
      field_value = $LOOK1.id
    }
  }

  response = {deleted: true}
  guid = "LOOK-OSD-2026-004"
}
