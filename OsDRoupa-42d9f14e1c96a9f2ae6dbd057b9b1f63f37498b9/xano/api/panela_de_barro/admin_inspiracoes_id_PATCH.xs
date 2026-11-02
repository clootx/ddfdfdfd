// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
query "adminInspiracoes/{inspiracao_id}" verb=PATCH {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int inspiracao_id? filters=min:1
    text status filters=trim
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

    precondition ($input.status == "Publicado" || $input.status == "Recusado") {
      error_type = "inputerror"
      error = "Escolha publicar ou recusar a inspiração."
    }

    db.get LOOK_INSPIRACAO {
      field_name = "id"
      field_value = $input.inspiracao_id
    } as $INSPIRACAO1

    precondition ($INSPIRACAO1 != null && $INSPIRACAO1.status != "Privado") {
      error_type = "notfound"
      error = "Inspiração não encontrada."
    }

    db.patch LOOK_INSPIRACAO {
      field_name = "id"
      field_value = $INSPIRACAO1.id
      data = {status: $input.status, moderado_em: now}
    } as $INSPIRACAO2
  }

  response = {ok: true, status: $INSPIRACAO2.status}
  guid = "FEED-OSD-2026-011"
}
