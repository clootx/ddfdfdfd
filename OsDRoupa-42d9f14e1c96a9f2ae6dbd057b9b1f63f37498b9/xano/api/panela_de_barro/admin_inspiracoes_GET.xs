// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
query adminInspiracoes verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
    } as $CURRENT_USER

    precondition ($CURRENT_USER != null && $CURRENT_USER.role == "admin") {
      error_type = "accessdenied"
      error = "Acesso restrito a administradores."
    }

    db.query LOOK_INSPIRACAO {
      where = $db.LOOK_INSPIRACAO.status != "Privado"
      sort = {LOOK_INSPIRACAO.created_at: "desc"}
      return = {type: "list", paging: {page: 1, per_page: 100, totals: false}}
    } as $INSPIRACOES1
  }

  response = {inspiracoes: $INSPIRACOES1.items}
  guid = "FEED-OSD-2026-010"
}
