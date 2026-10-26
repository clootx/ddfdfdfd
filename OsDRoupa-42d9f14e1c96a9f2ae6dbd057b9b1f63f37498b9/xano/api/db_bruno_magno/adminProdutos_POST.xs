// Criar produto no catálogo pela central de gestão.
query adminProdutos verb=POST {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    dblink {
      table = "PRODUTO"
    }
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
    } as $CURRENT_USER

    precondition ($CURRENT_USER != null && $CURRENT_USER.role == "admin") {
      error_type = "accessdenied"
      error = "Acesso restrito a administradores."
    }

    db.add PRODUTO {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $produto
  }

  response = $produto
  guid = "MGMT-OSD-ADMIN-003"
}
