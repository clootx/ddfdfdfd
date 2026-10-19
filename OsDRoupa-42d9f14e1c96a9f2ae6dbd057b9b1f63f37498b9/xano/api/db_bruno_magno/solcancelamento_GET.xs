// Query all SOLCANCELAMENTO records
query solcancelamento verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query SOLCANCELAMENTO {
      return = {type: "list"}
    } as $solcancelamento
  }

  response = $solcancelamento
  guid = "mBH5QhGLnnWO81ARrhcc9cz6-Cc"
}