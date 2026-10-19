// Query all FAQ records
query faq verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query FAQ {
      return = {type: "list"}
    } as $faq
  }

  response = $faq
  guid = "ij-nGExU0NrPGtRYVHi3H-4jDzo"
}