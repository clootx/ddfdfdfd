// Query all TESTE DA PORRA records
query teste_da_porra verb=GET {
  api_group = "Sendgrid Validation"

  input {
  }

  stack {
    db.query "" {
      return = {type: "list"}
    } as $teste_da_porra
  }

  response = $teste_da_porra
  guid = "cytLFZKWwhWDdrOUcezCRPnVcx0"
}