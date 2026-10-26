query adminRelatorios verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int page?=1 filters=min:1
    int per_page?=20 filters=min:1
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

    precondition ($input.per_page <= 100) {
      error_type = "inputerror"
      error = "A pagina pode conter no maximo 100 registros."
    }

    db.query PEDIDO {
      sort = {PEDIDO.created_at: "desc"}
      return = {
        type: "list",
        paging: {page: $input.page, per_page: $input.per_page, totals: true}
      }
    } as $RELATORIOS
  }

  response = $RELATORIOS
  guid = "MGMT-OSD-ADMIN-005"
}
