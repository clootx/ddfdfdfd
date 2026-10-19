// Get FAQ record
query "faq/{faq_id}" verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
    int faq_id? filters=min:1
  }

  stack {
    db.get FAQ {
      field_name = "id"
      field_value = $input.faq_id
    } as $faq
  
    precondition ($faq != null) {
      error_type = "notfound"
      error = "Not Found."
    }
  }

  response = $faq
  guid = "pRolZ4XkaTA2hOc1F5d9JJPWmxM"
}