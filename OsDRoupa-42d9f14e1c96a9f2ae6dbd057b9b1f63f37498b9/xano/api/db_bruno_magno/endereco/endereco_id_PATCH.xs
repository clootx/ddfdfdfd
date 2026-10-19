// Local draft. Validate and import in the Xano workspace before publishing.
query "endereco/{endereco_id}" verb=PATCH {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int endereco_id? filters=min:1
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

    db.get ENDERECO {
      field_name = "id"
      field_value = $input.endereco_id
    } as $ENDERECO1

    precondition ($ENDERECO1 != null && $ENDERECO1.cliente_id == $CLIENTE1.id) {
      error_type = "notfound"
      error = "Endereco nao encontrado."
    }

    db.patch ENDERECO {
      field_name = "id"
      field_value = $ENDERECO1.id
      data = {
        logradouro: $input.logradouro
        numero: $input.numero
        complemento: $input.complemento
        bairro: $input.bairro
        referencia: $input.referencia
        padrao: $input.padrao
        cep_id: $input.cep_id
      }
    } as $ENDERECO2

    conditional {
      if ($input.padrao == true) {
        db.query ENDERECO {
          where = $CLIENTE1.id == $db.ENDERECO.cliente_id && $ENDERECO2.id != $db.ENDERECO.id
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

  response = $ENDERECO2
  guid = "NfL9xrqcRAYBL9ORC12LwTkkoUg"
}