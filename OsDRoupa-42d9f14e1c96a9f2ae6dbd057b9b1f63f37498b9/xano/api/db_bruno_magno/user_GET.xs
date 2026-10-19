// Query all USER records
query user verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query USER {
      return = {type: "list"}
    } as $user
  }

  response = $user
  guid = "XTjRJqbCRkHAvt9gbUYU4QSZySk"
}