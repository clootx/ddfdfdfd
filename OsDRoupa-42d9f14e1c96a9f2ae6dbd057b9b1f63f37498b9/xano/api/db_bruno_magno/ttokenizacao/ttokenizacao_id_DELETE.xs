// Delete TTOKENIZACAO record.
query "ttokenizacao/{ttokenizacao_id}" verb=DELETE {
  api_group = "DB_BRUNO_MAGNO"
  auth = "user"

  input {
    int ttokenizacao_id? filters=min:1
  }

  stack {
    db.get user {
      field_name = "id"
      field_value = $auth.id
    } as $CURRENT_USER

    precondition ($CURRENT_USER != null && $CURRENT_USER.role == "admin") {
      error_type = "accessdenied"
      error = "Acesso restrito à administração."
    }
    db.del TTOKENIZACAO {
      field_name = "id"
      field_value = $input.ttokenizacao_id
    }
  }

  response = null
  guid = "0jMeZP2H_VdrXYCNFP-mt0z7K70"
}