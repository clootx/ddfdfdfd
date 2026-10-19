// Local draft. Validate and import in the Xano workspace before publishing.
query meuArmario verb=GET {
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

    db.query ROUPA_CLIENTE {
      where = $var.CLIENTE1.id == $db.ROUPA_CLIENTE.cliente_id
      sort = {ROUPA_CLIENTE.created_at: "desc"}
      return = {type: "list"}
    } as $ROUPAS1
  }

  response = {itens: $ROUPAS1}
  guid = "WARDROBE-OSD-2026-002"
}
