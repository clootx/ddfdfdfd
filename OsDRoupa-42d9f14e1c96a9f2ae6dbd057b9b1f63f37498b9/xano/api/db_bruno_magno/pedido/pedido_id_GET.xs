// Get PEDIDO record
query "pedido/{pedido_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int pedido_id? filters=min:1
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
    } as $CURRENT_USER

    precondition ($CURRENT_USER != null && $CURRENT_USER.role == "admin") {
      error_type = "accessdenied"
      error = "Acesso restrito à administração."
    }
    db.get PEDIDO {
      field_name = "id"
      field_value = $input.pedido_id
    } as $pedido
  
    precondition ($pedido != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $pedido
  guid = "lOE1xSUCjkf65c2_rzNN9a_QUNc"
}