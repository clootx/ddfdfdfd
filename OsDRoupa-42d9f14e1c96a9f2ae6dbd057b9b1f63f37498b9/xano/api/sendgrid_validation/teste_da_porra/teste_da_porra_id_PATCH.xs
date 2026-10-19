// Edit TESTE DA PORRA record
query "teste_da_porra/{teste_da_porra_id}" verb=PATCH {
  api_group = "Sendgrid Validation"

  input {
    int teste_da_porra_id? filters=min:1
    dblink {
      table = ""
    }
  }

  stack {
    util.get_raw_input {
      encoding = "json"
      exclude_middleware = false
    } as $raw_input
  
    db.patch "" {
      field_name = "id"
      field_value = $input.teste_da_porra_id
      data = `$input|pick:($raw_input|keys)`|filter_null|filter_empty_text
    } as $teste_da_porra
  }

  response = $teste_da_porra
  guid = "rFNhKFCZuPbeuQG9fBpx35Wwn9o"
}