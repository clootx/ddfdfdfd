// Local draft (Change 030). Validate and import in the Xano workspace before publishing.
// Pontos a conferir no import: filtro de chaves do armário da própria conta (no SQLite, chaves de
// outras contas são descartadas; aqui o rascunho só limita a quantidade) e o filtro `in`.
query feedbackLooks verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text nome? filters=trim|max:80
    text[] roupa_chaves?
    text avaliacao filters=trim
    text motivo? filters=trim|max:60
    text ocasiao? filters=trim|max:40
    text clima? filters=trim|max:30
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

    precondition ($input.avaliacao == "positivo" || $input.avaliacao == "negativo") {
      error_type = "inputerror"
      error = "Avaliação inválida."
    }

    precondition ($input.avaliacao == "positivo" || ($input.motivo|in:["Não combina comigo", "Não serve para o clima", "Não serve para a ocasião", "Pouco confortável", "Já uso muito essas peças", "Outro motivo"])) {
      error_type = "inputerror"
      error = "Escolha um motivo válido."
    }

    precondition ((($input.roupa_chaves ?? [])|count) <= 12) {
      error_type = "inputerror"
      error = "Peças inválidas."
    }

    db.add FEEDBACK_LOOK {
      data = {
        cliente_id  : $CLIENTE1.id
        nome        : $input.nome
        roupa_chaves: $input.roupa_chaves ?? []
        avaliacao   : $input.avaliacao
        motivo      : ($input.avaliacao == "positivo") ? "" : $input.motivo
        ocasiao     : $input.ocasiao
        clima       : $input.clima
      }
    } as $FEEDBACK1
  }

  response = {id: $FEEDBACK1.id, ok: true}
  guid = "STYLE-OSD-2026-003"
}
