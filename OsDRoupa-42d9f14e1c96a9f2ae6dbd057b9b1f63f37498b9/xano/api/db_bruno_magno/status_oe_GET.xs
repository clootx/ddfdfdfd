// Query all STATUS_OE records
query status_oe verb=GET {
  api_group = "DB_BRUNO_MAGNO"

  input {
  }

  stack {
    db.query STATUS_OE {
      return = {type: "list"}
    } as $status_oe
  }

  response = $status_oe
  guid = "4-FEKokwMRQYfUl8tYA69U_VT9U"
}