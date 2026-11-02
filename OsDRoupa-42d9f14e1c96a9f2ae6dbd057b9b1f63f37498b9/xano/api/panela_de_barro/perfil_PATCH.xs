// Rascunho local: importar e validar no workspace Xano antes de publicar.
query perfil verb=PATCH {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text nome? filters=trim|min:3|max:120
    text celular? filters=trim|min:6|max:30
    text data_nascimento? filters=trim|max:10
    text pronome? filters=trim|max:40
    text estilo_preferido? filters=trim|max:50
    text tamanho_superior? filters=trim|max:24
    text tamanho_inferior? filters=trim|max:24
    text tamanho_calcado? filters=trim|max:24
    text cores_favoritas? filters=trim|max:100
    text sobre_mim? filters=trim|max:240
    bool personalizacao_ia?
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "notfound"
      error = "Cliente não encontrado para esta conta."
    }

    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $RAW_INPUT1

    db.patch CLIENTE {
      field_name = "id"
      field_value = $CLIENTE1.id
      data = `$input|pick:($RAW_INPUT1|keys)`|filter_null
    } as $CLIENTE2
  }

  response = $CLIENTE2
  tags = ["perfil", "cliente"]
  guid = "PROFILE-OSD-2026-001"
}
