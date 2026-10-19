// Local draft. Validate and import in the Xano workspace before publishing.
query buscaCliente verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "notfound"
      error = "Cliente nao encontrado para esta conta."
    }
  }

  response = $CLIENTE1
  tags = ["modulo 06", "perfil"]
  guid = "utu4NoVMpAGd6tSFnC8-AOXKalg"
}
