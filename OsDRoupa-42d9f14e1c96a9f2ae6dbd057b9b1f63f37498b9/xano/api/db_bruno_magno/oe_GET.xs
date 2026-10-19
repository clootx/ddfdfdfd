// Query all OE records
query oe verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query OE {
      return = {type: "list"}
    } as $oe
  }

  response = $oe
  guid = "hKq2QJZmtuQS3QW2sqDGIa01wY0"
}