// Published in Xano workspace 147975, live branch v1; filtered by authenticated owner.
query meusDispositivos verb=GET {
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
      error = "Cliente n\u00e3o encontrado para esta conta."
    }

    db.query DISPOSITIVO_ARMARIO {
      where = $var.CLIENTE1.id == $db.DISPOSITIVO_ARMARIO.cliente_id
      sort = {DISPOSITIVO_ARMARIO.created_at: "desc"}
      return = {type: "list"}
    } as $DISPOSITIVOS1
  }

  response = {dispositivos: $DISPOSITIVOS1}
  guid = "IOT-OSD-2026-004"
}
