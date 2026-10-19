// Get TESTE DA PORRA record
query "teste_da_porra/{teste_da_porra_id}" verb=GET {
  api_group = "Sendgrid Validation"

  input {
    int teste_da_porra_id? filters=min:1
  }

  stack {
    db.get "" {
      field_name = "id"
      field_value = $input.teste_da_porra_id
    } as $teste_da_porra
  
    precondition ($teste_da_porra != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $teste_da_porra
  guid = "7zu1KAIpeN80me6WCC6TAI7tvsI"
}