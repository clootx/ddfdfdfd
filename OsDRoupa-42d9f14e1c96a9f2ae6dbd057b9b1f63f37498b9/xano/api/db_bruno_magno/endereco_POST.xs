// Local draft. Validate and import in the Xano workspace before publishing.
query endereco verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    text logradouro filters=trim
    text numero filters=trim
    text? complemento? filters=trim
    text bairro filters=trim
    text? referencia? filters=trim
    bool padrao?=false
    int cep_id filters=min:1
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente nao encontrado para esta conta."
    }

    db.add ENDERECO {
      enforce_hidden_fields = false
      data = {
        cliente_id: $CLIENTE1.id
        logradouro: $input.logradouro
        numero: $input.numero
        complemento: $input.complemento
        bairro: $input.bairro
        referencia: $input.referencia
        padrao: $input.padrao
        cep_id: $input.cep_id
      }
    } as $ENDERECO1

    conditional {
      if ($input.padrao == true) {
        db.query ENDERECO {
          where = $CLIENTE1.id == $db.ENDERECO.cliente_id && $ENDERECO1.id != $db.ENDERECO.id
          return = {type: "list"}
        } as $OUTROS1

        array.map ($OUTROS1) {
          by = {id: $this.id, padrao: false}
        } as $ALTERACOES1

        db.bulk.patch ENDERECO {
          items = $ALTERACOES1
        } as $OUTROS_ATUALIZADOS1
      }
    }
  }

  response = $ENDERECO1
  guid = "QvnOez-JSiV2yA8ss3qrVAnYZzI"
}