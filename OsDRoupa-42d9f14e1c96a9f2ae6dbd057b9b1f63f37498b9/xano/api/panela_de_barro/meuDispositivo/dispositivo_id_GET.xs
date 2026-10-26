// Published in Xano workspace 147975, live branch v1; filtered by authenticated owner.
query "meuDispositivo/{dispositivo_id}" verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int dispositivo_id? filters=min:1
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente nao encontrado para esta conta."
    }

    db.get DISPOSITIVO_ARMARIO {
      field_name = "id"
      field_value = $input.dispositivo_id
    } as $DISPOSITIVO1

    precondition ($DISPOSITIVO1 != null && $DISPOSITIVO1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Dispositivo nao encontrado."
    }

    db.query EVENTO_DISPOSITIVO {
      where = $var.DISPOSITIVO1.id == $db.EVENTO_DISPOSITIVO.dispositivo_id
      sort = {EVENTO_DISPOSITIVO.ocorrido_em: "desc"}
      return = {type: "list"}
    } as $EVENTOS1
  }

  response = {dispositivo: $DISPOSITIVO1, eventos: $EVENTOS1}
  guid = "IOT-OSD-2026-005"
}
