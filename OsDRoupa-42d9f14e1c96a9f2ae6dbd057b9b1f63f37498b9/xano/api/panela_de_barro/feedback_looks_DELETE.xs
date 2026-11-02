// Local draft (Change 030). Validate and import in the Xano workspace before publishing.
// Apaga todo o histórico de avaliações da conta (direito de exclusão).
query feedbackLooks verb=DELETE {
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
      return = {type: "list"}
    } as $FEEDBACKS1

    foreach ($FEEDBACKS1) {
      each as $FEEDBACK1 {
        db.del FEEDBACK_LOOK {
          field_name = "id"
          field_value = $FEEDBACK1.id
        }
      }
    }
  }

  response = {apagados: $FEEDBACKS1|count, ok: true}
  guid = "STYLE-OSD-2026-004"
}
