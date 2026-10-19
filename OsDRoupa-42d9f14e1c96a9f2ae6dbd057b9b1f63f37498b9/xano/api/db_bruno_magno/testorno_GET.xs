// Query all TESTORNO records
query testorno verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query TESTORNO {
      return = {type: "list"}
    } as $testorno
  }

  response = $testorno
  guid = "6w5C4CxOgdsqN3RNFIiJDA5SkCs"
}