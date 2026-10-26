query concluirDesafio verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text desafio_id filters=trim
  }

  stack {
    precondition (
      $input.desafio_id == "repeat-three" ||
      $input.desafio_id == "forgotten-piece" ||
      $input.desafio_id == "care-routine" ||
      $input.desafio_id == "plan-week" ||
      $input.desafio_id == "repair-one" ||
      $input.desafio_id == "color-repeat" ||
      $input.desafio_id == "wear-log" ||
      $input.desafio_id == "closet-review"
    ) {
      error_type = "inputerror"
      error = "Desafio inválido."
    }

    db.query DESAFIO_CONCLUIDO {
      where = $auth.id == $db.DESAFIO_CONCLUIDO.user_id && $input.desafio_id == $db.DESAFIO_CONCLUIDO.desafio_id
      return = {type: "single"}
    } as $EXISTENTE1

    conditional {
      if ($EXISTENTE1 == null) {
        db.add DESAFIO_CONCLUIDO {
          data = {
            user_id    : $auth.id
            desafio_id : $input.desafio_id
          }
        } as $CONCLUIDO1
      }
      else {
        var $CONCLUIDO1 {
          value = $EXISTENTE1
        }
      }
    }
  }

  response = {concluido: $CONCLUIDO1}
  guid = "CONTENT-OSD-2026-003"
}
