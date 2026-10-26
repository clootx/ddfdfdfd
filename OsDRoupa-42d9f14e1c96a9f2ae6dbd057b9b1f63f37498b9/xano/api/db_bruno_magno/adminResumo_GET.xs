query adminResumo verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
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

    db.query PEDIDO {
      return = {type: "count"}
    } as $PEDIDOS_COUNT

    db.query PRODUTO {
      return = {type: "count"}
    } as $PRODUTOS_COUNT

    db.query CLIENTE {
      return = {type: "count"}
    } as $CLIENTES_COUNT
  }

  response = {
    resumo: {
      pedidos_cadastrados: $PEDIDOS_COUNT,
      vendas_mes: "Aguardando conciliacao de pagamentos",
      produtos_cadastrados: $PRODUTOS_COUNT,
      clientes_cadastrados: $CLIENTES_COUNT
    }
  }
  guid = "MGMT-OSD-ADMIN-001"
}
