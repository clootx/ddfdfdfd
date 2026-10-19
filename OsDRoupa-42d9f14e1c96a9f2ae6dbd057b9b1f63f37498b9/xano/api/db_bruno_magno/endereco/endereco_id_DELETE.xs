// Local draft. Validate and import in the Xano workspace before publishing.
query "endereco/{endereco_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int endereco_id? filters=min:1
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

    db.del ENDERECO {
      field_name = "id"
      field_value = $ENDERECO1.id
    }
  }

  response = {deleted: true}
  guid = "rmNXJu84_4yciqT3jgbie7M1dtM"
}