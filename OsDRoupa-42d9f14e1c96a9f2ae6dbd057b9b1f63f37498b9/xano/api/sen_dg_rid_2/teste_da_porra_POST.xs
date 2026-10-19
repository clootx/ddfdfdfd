// Add TESTE DA PORRA record
query teste_da_porra verb=POST {
  api_group = "SENDgRID2"

  input {
    dblink {
      table = ""
    }
  }

  stack {
    db.get "" {
      field_name = "email"
      field_value = $input.email
    } as $TESTE_DA_PORRA1
  
    security.random_number {
      min = 10000
      max = 999999
    } as $codigo_otp
  
    var $expiracao {
      value = now|add_ms_to_timestamp:330
    }
  
    db.edit "" {
      field_name = "id"
      field_value = $TESTE_DA_PORRA1.id
      enforce_hidden_fields = false
      data = {}
    } as $TESTE_DA_PORRA2
  }

  response = $model
  tags = ["modulo 01"]
  guid = "6ygoOs4QgiT5u1fHet9b_xSaNI4"
}