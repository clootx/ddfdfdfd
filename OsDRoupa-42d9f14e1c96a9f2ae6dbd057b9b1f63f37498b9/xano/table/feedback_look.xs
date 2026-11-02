// Local draft (Change 030). Validate and import in the Xano workspace before publishing.
// Feedback 👍/👎 dos looks da IA; gravado só por ação explícita da pessoa.
table FEEDBACK_LOOK {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int cliente_id {
      table = "CLIENTE"
    }
    text nome? filters=trim|max:80
    json roupa_chaves?
    enum avaliacao {
      values = ["positivo", "negativo"]
    }
    text motivo? filters=trim|max:60
    text ocasiao? filters=trim|max:40
    text clima? filters=trim|max:30
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {
      type : "btree"
      field: [
        {name: "cliente_id", op: "asc"}
        {name: "created_at", op: "desc"}
      ]
    }
  ]

  tags = ["change 030", "estilista", "feedback"]
  guid = "STYLE-OSD-2026-001"
}
