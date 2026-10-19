// Delete TESTE DA PORRA record.
query "teste_da_porra/{teste_da_porra_id}" verb=DELETE {
  api_group = "Sendgrid Validation"

  input {
    int teste_da_porra_id? filters=min:1
  }

  stack {
    db.del "" {
      field_name = "id"
      field_value = $input.teste_da_porra_id
    }
  }

  response = null
  guid = "p-9rX_KnXuLXA6XwSLK3Snn6Yrk"
}