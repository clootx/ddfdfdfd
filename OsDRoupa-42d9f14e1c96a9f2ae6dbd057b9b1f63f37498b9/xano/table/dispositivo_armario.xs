// Local draft. Validate and import in the Xano workspace before publishing.
table DISPOSITIVO_ARMARIO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
    int? cliente_id? {
      table = "CLIENTE"
      visibility = "private"
    }
    text identificador filters=trim {
      visibility = "private"
    }
    text nome filters=trim
    text tipo filters=trim
    text? versao_firmware? filters=trim {
      visibility = "private"
    }
    enum status?="sem_contato" {
      values = ["pareamento_pendente", "conectado", "sem_contato"]
    }
    text? chave_publica? {
      visibility = "private"
    }
    timestamp? ultimo_contato?
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "identificador", op: "asc"}]}
    {type: "btree", field: [{name: "cliente_id", op: "asc"}]}
    {type: "btree", field: [{name: "ultimo_contato", op: "desc"}]}
  ]

  tags = ["modulo 12", "armario-inteligente"]
  guid = "IOT-OSD-2026-001"
}
