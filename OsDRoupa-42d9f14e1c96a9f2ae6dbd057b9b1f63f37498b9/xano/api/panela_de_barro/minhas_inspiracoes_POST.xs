// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
// O Reflex já remove fotos do armário (data URI) das peças; aqui a regra é repetida no servidor.
query minhasInspiracoes verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text chave_local filters=trim|max:64
    text nome filters=trim|max:80
    text ocasiao filters=trim
    text? clima?="" filters=trim
    text? regiao?="" filters=trim
    text? estacao?="" filters=trim|max:20
    text? paleta?="" filters=trim|max:200
    text? tecidos?="" filters=trim|max:200
    text? justificativa?="" filters=trim|max:1200
    text? nota?="" filters=trim|max:4
    json pecas
    text? imagem?="" filters=trim|max:60
  }

  stack {
    precondition ($input.chave_local != "" && $input.nome != "") {
      error_type = "inputerror"
      error = "Informe a chave e o nome da inspiração."
    }

    precondition (
      $input.ocasiao == "Dia a dia" || $input.ocasiao == "Trabalho" || $input.ocasiao == "Evento" ||
      $input.ocasiao == "Viagem" || $input.ocasiao == "Outro"
    ) {
      error_type = "inputerror"
      error = "Ocasião inválida."
    }

    precondition (($input.pecas|count) > 0 && ($input.pecas|count) <= 12) {
      error_type = "inputerror"
      error = "A inspiração precisa ter de 1 a 12 peças."
    }

    precondition ($input.imagem == "" || ($input.imagem|starts_with:"looks/")) {
      error_type = "inputerror"
      error = "Imagem da inspiração inválida."
    }

    precondition (($input.pecas|json_encode|contains:"data:") == false) {
      error_type = "inputerror"
      error = "Fotos do armário não podem ser enviadas para inspirações."
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
      field_name = "chave_local"
      field_value = $input.chave_local
    } as $EXISTENTE1

    precondition ($EXISTENTE1 == null || $EXISTENTE1.cliente_id == $CLIENTE1.id) {
      error_type = "accessdenied"
      error = "A chave já está vinculada a outra conta."
    }

    conditional {
      if ($EXISTENTE1 == null) {
        db.add LOOK_INSPIRACAO {
          enforce_hidden_fields = false
          data = {
            cliente_id   : $CLIENTE1.id
            chave_local  : $input.chave_local
            nome         : $input.nome
            ocasiao      : $input.ocasiao
            clima        : $input.clima
            regiao       : $input.regiao
            estacao      : $input.estacao
            paleta       : $input.paleta
            tecidos      : $input.tecidos
            justificativa: $input.justificativa
            nota         : $input.nota
            pecas        : $input.pecas
            imagem       : $input.imagem
            status       : "Privado"
          }
        } as $INSPIRACAO1
      }
      else {
        var $INSPIRACAO1 {
          value = $EXISTENTE1
        }
      }
    }
  }

  response = {inspiracao: $INSPIRACAO1}
  guid = "FEED-OSD-2026-005"
}
