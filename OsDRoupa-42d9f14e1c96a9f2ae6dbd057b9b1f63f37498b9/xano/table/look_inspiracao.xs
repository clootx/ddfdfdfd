// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
table LOOK_INSPIRACAO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int cliente_id {
      table = "CLIENTE"
    }
    text chave_local filters=trim
    text nome filters=trim
    text ocasiao filters=trim
    text? clima? filters=trim
    text? regiao? filters=trim
    text? estacao? filters=trim
    text? paleta? filters=trim
    text? tecidos? filters=trim
    text? justificativa? filters=trim
    text? nota? filters=trim
    json pecas
    text? imagem? filters=trim
    text status?="Privado" filters=trim
    timestamp? moderado_em?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "chave_local", op: "asc"}]}
    {
      type : "btree"
      field: [
        {name: "status", op: "asc"}
        {name: "created_at", op: "desc"}
      ]
    }
    {type: "btree", field: [{name: "cliente_id", op: "asc"}]}
  ]

  tags = ["change 028", "inspiracao", "feed"]
  guid = "FEED-OSD-2026-001"
}
