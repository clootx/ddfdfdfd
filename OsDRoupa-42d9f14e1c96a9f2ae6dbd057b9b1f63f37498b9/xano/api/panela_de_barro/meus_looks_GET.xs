// Local draft. Validate and import in the Xano workspace before publishing.
query meusLooks verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
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

    db.query LOOK_CLIENTE {
      where = $CLIENTE1.id == $db.LOOK_CLIENTE.cliente_id
      return = {type: "list"}
      sort = {LOOK_CLIENTE.data_planejada: "asc"}
    } as $LOOKS1
  }

  response = {looks: $LOOKS1}
  guid = "LOOK-OSD-2026-002"
}
