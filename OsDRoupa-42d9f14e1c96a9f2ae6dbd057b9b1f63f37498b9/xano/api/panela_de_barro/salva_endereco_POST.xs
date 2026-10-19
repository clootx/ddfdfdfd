// Local draft. Validate and import in the Xano workspace before publishing.
query salvaEndereco verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text logradouro filters=trim
    text numero filters=trim
    text? complemento? filters=trim
    text bairro filters=trim
    text? referencia? filters=trim
    bool padrao?=false
    text cep filters=trim
    text uf filters=trim
    text cidade filters=trim
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

    api.request {
      url = "https://x8ki-letl-twmt.n7.xano.io/api:6LtoY7Zt/UpsertCEP"
      method = "POST"
      params = {cep: $input.cep, uf: $input.uf, cidade: $input.cidade}
      headers = ["Content-Type: application/json"]
    } as $CEP1

    precondition ($CEP1.response.status == 200 && $CEP1.response.result.id != null) {
      error_type = "inputerror"
      error = "Nao foi possivel validar o CEP."
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
        cep_id: $CEP1.response.result.id
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

  response = {endereco: $ENDERECO1}
  guid = "dCCuXjeseL85_e5BtrRH1e5KFjk"
}