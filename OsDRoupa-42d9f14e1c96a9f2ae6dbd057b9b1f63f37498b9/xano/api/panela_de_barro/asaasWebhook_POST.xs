// Rascunho local. Cadastre ASAAS_WEBHOOK_TOKEN como segredo do ambiente Xano antes de publicar.
query asaasWebhook verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "none"

  input {
    text id filters=trim
    text event filters=trim
    json payment
  }

  stack {
    // LEGADO DESATIVADO: use Mercado Pago pelo backend SQLite ate publicar a migracao Xano.
    precondition (false) {
      error_type = "standard"
      error = "Asaas desativado. Configure o checkout Mercado Pago no backend antes de usar o Xano."
    }
    precondition (
      $env.ASAAS_WEBHOOK_TOKEN != null &&
      $env.ASAAS_WEBHOOK_TOKEN != "" &&
      ($env.$http_headers|get:"asaas-access-token") == $env.ASAAS_WEBHOOK_TOKEN
    ) {
      error_type = "accessdenied"
      error = "Assinatura do webhook inválida."
    }

    precondition ($input.id != "" && $input.event != "" && $input.payment.id != null) {
      error_type = "inputerror"
      error = "Evento Asaas incompleto."
    }

    db.get EVENTO_ASAAS {
      field_name = "event_id"
      field_value = $input.id
    } as $EXISTINGEVENT1

    var $EVENT1 {
      value = {}
    }
    var $DUPLICATE1 {
      value = false
    }

    conditional {
      if ($EXISTINGEVENT1 != null && $EXISTINGEVENT1.processed == true) {
        var.update $EVENT1 {
          value = $EXISTINGEVENT1
        }
        var.update $DUPLICATE1 {
          value = true
        }
      }
      elseif ($EXISTINGEVENT1 == null) {
        db.add EVENTO_ASAAS {
          enforce_hidden_fields = false
          data = {
            event_id: $input.id,
            event_name: $input.event,
            payment_id: $input.payment.id,
            processed: false
          }
        } as $NEWEVENT1

        var.update $EVENT1 {
          value = $NEWEVENT1
        }
      }
      else {
        var.update $EVENT1 {
          value = $EXISTINGEVENT1
        }
      }
    }

    conditional {
      if ($DUPLICATE1 == false) {
        db.query TRANSACAO {
          where = $input.payment.id == $db.TRANSACAO.idpayment
          return = {type: "single"}
        } as $TRANSACTION1

        precondition ($TRANSACTION1 != null && $TRANSACTION1.pedido_id != null) {
          error_type = "notfound"
          error = "Cobrança do evento não encontrada no OSDROUPA."
        }

        db.get PEDIDO {
          field_name = "id"
          field_value = $TRANSACTION1.pedido_id
        } as $ORDER1

        precondition ($ORDER1 != null && $ORDER1.Total == $input.payment.value) {
          error_type = "inputerror"
          error = "Valor do webhook não corresponde ao pedido registrado."
        }

        var $EXPECTEDREFERENCE1 {
          value = "OSD-" ~ ($ORDER1.cliente_id|to_text) ~ "-" ~ $ORDER1.chave_idempotencia
        }

        precondition (
          $input.payment.customer == $TRANSACTION1.clienteassas &&
          $input.payment.externalReference == $EXPECTEDREFERENCE1
        ) {
          error_type = "accessdenied"
          error = "A cobrança recebida não corresponde ao cliente ou à referência do pedido."
        }

        conditional {
          if ($input.event == "PAYMENT_RECEIVED" && $input.payment.status == "RECEIVED") {
            db.transaction {
              stack {
                db.patch TRANSACAO {
                  field_name = "id"
                  field_value = $TRANSACTION1.id
                  data = {
                    status_gateway  : $input.payment.status
                    pago_confirmado : true
                    confirmado_em   : now
                  }
                }

                db.patch PEDIDO {
                  field_name = "id"
                  field_value = $ORDER1.id
                  data = {pagamento_status: "Pago"}
                }

                db.patch EVENTO_ASAAS {
                  field_name = "id"
                  field_value = $EVENT1.id
                  data = {
                    pedido_id: $ORDER1.id,
                    processed: true,
                    processing_error: null
                  }
                }
              }
            }
          }
          else {
            db.patch TRANSACAO {
              field_name = "id"
              field_value = $TRANSACTION1.id
              data = {status_gateway: $input.payment.status}
            }

            db.patch EVENTO_ASAAS {
              field_name = "id"
              field_value = $EVENT1.id
              data = {
                pedido_id: $ORDER1.id,
                processed: true,
                processing_error: null
              }
            }
          }
        }
      }
    }
  }

  response = {
    received: true,
    duplicate: $DUPLICATE1,
    processed: true
  }
  guid = "ORDERS-OSD-2026-004"
}
