// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
// Envia para moderação; só aparece no feed depois de aprovada por um administrador.
query "publicarInspiracao/{inspiracao_id}" verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int inspiracao_id? filters=min:1
    bool autorizo_publicacao?=false
  }

  stack {
    precondition ($input.autorizo_publicacao == true) {
      error_type = "inputerror"
      error = "Autorize a publicação anônima para enviar ao feed."
    }

    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }

    db.get LOOK_INSPIRACAO {
      field_name = "id"
      field_value = $input.inspiracao_id
    } as $INSPIRACAO1

    precondition (
      $INSPIRACAO1 != null && $INSPIRACAO1.cliente_id == $CLIENTE1.id &&
      ($INSPIRACAO1.status == "Privado" || $INSPIRACAO1.status == "Recusado")
    ) {
      error_type = "notfound"
      error = "Inspiração não encontrada ou já enviada."
    }

    db.patch LOOK_INSPIRACAO {
      field_name = "id"
      field_value = $INSPIRACAO1.id
      data = {status: "Pendente", moderado_em: null}
    } as $INSPIRACAO2
  }

  response = {ok: true, status: $INSPIRACAO2.status}
  guid = "FEED-OSD-2026-007"
}
