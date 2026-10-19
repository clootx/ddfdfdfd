// Query all STATUS_TESTORNO records
query status_testorno verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_TESTORNO {
      return = {type: "list"}
    } as $status_testorno
  }

  response = $status_testorno
  guid = "QYoXQq-HIFl2f3RA1NLMdAyLoL0"
}