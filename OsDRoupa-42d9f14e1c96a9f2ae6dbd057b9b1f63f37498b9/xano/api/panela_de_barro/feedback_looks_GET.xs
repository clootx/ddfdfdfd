// Local draft (Change 030). Validate and import in the Xano workspace before publishing.
query feedbackLooks verb=GET {
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

    db.query FEEDBACK_LOOK {
      where = $db.FEEDBACK_LOOK.cliente_id == $CLIENTE1.id
      sort = {FEEDBACK_LOOK.created_at: "desc"}
      output = ["id", "created_at", "nome", "roupa_chaves", "avaliacao", "motivo", "ocasiao", "clima"]
      return = {type: "list", paging: {page: 1, per_page: 30, totals: false}}
    } as $FEEDBACKS1
  }

  response = {feedbacks: $FEEDBACKS1.items}
  guid = "STYLE-OSD-2026-002"
}
