// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
query minhasInspiracoes verb=GET {
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

    db.query LOOK_INSPIRACAO {
      where = $db.LOOK_INSPIRACAO.cliente_id == $CLIENTE1.id
      sort = {LOOK_INSPIRACAO.created_at: "desc"}
      return = {type: "list"}
    } as $CRIADAS1

    db.query INSPIRACAO_SALVA {
      where = $db.INSPIRACAO_SALVA.cliente_id == $CLIENTE1.id
      return = {type: "list"}
    } as $MARCAS1

    var $IDS_SALVOS {
      value = $MARCAS1|map:$$.inspiracao_id
    }

    db.query LOOK_INSPIRACAO {
      where = $db.LOOK_INSPIRACAO.id in $IDS_SALVOS && $db.LOOK_INSPIRACAO.status == "Publicado"
      output = ["id", "created_at", "nome", "ocasiao", "clima", "regiao", "estacao", "paleta", "tecidos", "justificativa", "nota", "pecas", "imagem"]
      return = {type: "list"}
    } as $SALVAS1
  }

  response = {criadas: $CRIADAS1, salvas: $SALVAS1}
  guid = "FEED-OSD-2026-004"
}
