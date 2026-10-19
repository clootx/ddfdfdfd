table TESTORNO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    decimal Valor?="10.2"
    int solcancelamento_id? {
      table = "SOLCANCELAMENTO"
    }
  
    int? status_testorno_id?=1 {
      table = "STATUS_TESTORNO"
    }
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 05"]
  guid = "3mk3CsB3pv6vud2CsTi90kD-naU"
}