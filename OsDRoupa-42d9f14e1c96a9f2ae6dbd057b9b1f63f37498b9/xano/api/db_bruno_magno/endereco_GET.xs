// Local draft. Validate and import in the Xano workspace before publishing.
query endereco verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
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

    db.query ENDERECO {
      where = $CLIENTE1.id == $db.ENDERECO.cliente_id
      sort = {ENDERECO.created_at: "desc"}
      return = {type: "list"}
    } as $ENDERECOS1
  }

  response = $ENDERECOS1
  guid = "o-6_U7SmWa5LQ4bgM0TylbbcaIw"
}