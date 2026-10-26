query adminClientes verb=GET {
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

    db.query CLIENTE {
      sort = {CLIENTE.created_at: "desc"}
      addon = [
        {name: "STATUS_CLIENTE", input: {status_cliente_id: $output.status_cliente_id}, as: "status"}
      ]
      return = {
        type: "list",
        paging: {page: $input.page, per_page: $input.per_page, totals: true}
      }
    } as $CLIENTES
  }

  response = $CLIENTES
  guid = "MGMT-OSD-ADMIN-004"
}
