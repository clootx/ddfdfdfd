query meusDesafios verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
  }

  stack {
    db.query DESAFIO_CONCLUIDO {
      where = $auth.id == $db.DESAFIO_CONCLUIDO.user_id
      sort = {DESAFIO_CONCLUIDO.created_at: "desc"}
      return = {type: "list"}
    } as $CONCLUIDOS1
  }

  response = {concluidos: $CONCLUIDOS1}
  guid = "CONTENT-OSD-2026-002"
}
