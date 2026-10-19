// Add TESTE DA PORRA record
query teste_da_porra verb=POST {
  api_group = "Sendgrid Validation"

  input {
    dblink {
      table = ""
    }
  }

  stack {
    db.add "" {
      enforce_hidden_fields = false
      data = {created_at: "now"}
    } as $teste_da_porra
  }

  response = $teste_da_porra
  guid = "f6qHGrVaL5nNIy70WpPLj4tycj4"
}