// Rascunho local. Configure ASAAS_API_KEY no ambiente Xano e valide no sandbox antes de importar/publicar.
query checkoutPedido verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int endereco_id? filters=min:1
    enum tipo {
      values = ["PIX"]
    }
    json itens
    text chave_idempotencia filters=trim|min:16|max:100
  }

  stack {
    // LEGADO DESATIVADO: use Mercado Pago pelo backend SQLite ate publicar a migracao Xano.
    precondition (false) {
      error_type = "standard"
      error = "Asaas desativado. Configure o checkout Mercado Pago no backend antes de usar o Xano."
    }
    precondition (($input.itens|count) >= 1 && ($input.itens|count) <= 20) {
      error_type = "inputerror"
      error = "O pedido precisa conter de 1 a 20 produtos."
    }

    precondition ($env.ASAAS_API_KEY != null && $env.ASAAS_API_KEY != "") {
      error_type = "standard"
      error = "Integração PIX não configurada no Xano."
    }

    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }

    db.get ENDERECO {
      field_name = "id"
      field_value = $input.endereco_id
    } as $ENDERECO1

    precondition ($ENDERECO1 != null && $ENDERECO1.cliente_id == $CLIENTE1.id) {
      error_type = "accessdenied"
      error = "Endereço não pertence a esta conta."
    }

    db.get CARTAOTOKNZD {
      field_name = "cliente_id"
      field_value = $CLIENTE1.id
    } as $ASAASCLIENTE1

    precondition ($ASAASCLIENTE1 != null && $ASAASCLIENTE1.Codigoclienteassas != "") {
      error_type = "standard"
      error = "O cadastro de pagamento desta conta ainda não está pronto."
    }

    var $ASSINATURA1 {
      value = {metodo: "PIX", endereco_id: $input.endereco_id, itens: $input.itens}|json_encode
    }

    db.query PEDIDO {
      where = $CLIENTE1.id == $db.PEDIDO.cliente_id && $input.chave_idempotencia == $db.PEDIDO.chave_idempotencia
      return = {type: "single"}
    } as $EXISTINGORDER1

    var $PEDIDO1 {
      value = {}
    }
    var $TOTAL1 {
      value = 0
    }
    var $ITEMSNORMALIZED1 {
      value = []
    }
    var $EXTERNALREFERENCE1 {
      value = "OSD-" ~ ($CLIENTE1.id|to_text) ~ "-" ~ $input.chave_idempotencia
    }

    conditional {
      if ($EXISTINGORDER1 != null) {
        precondition (
          $EXISTINGORDER1.endereco_id == $input.endereco_id &&
          $EXISTINGORDER1.assinatura_checkout == $ASSINATURA1
        ) {
          error_type = "inputerror"
          error = "A chave de idempotência já foi usada para outro carrinho ou endereço."
        }

        var.update $PEDIDO1 {
          value = $EXISTINGORDER1
        }
        var.update $TOTAL1 {
          value = $EXISTINGORDER1.Total
        }
      }
      else {

        foreach ($input.itens) {
          each as $LINE1 {

            db.get PRODUTO {
              field_name = "id"
              field_value = $LINE1.produto_id
            } as $PRODUCT1

            precondition ($PRODUCT1 != null && $PRODUCT1.Categoria != null && $PRODUCT1.Categoria != "") {
              error_type = "notfound"
              error = "Produto não encontrado ou ainda não classificado para a loja de moda."
            }

            precondition ($PRODUCT1.demonstracao != true) {
              error_type = "inputerror"
              error = "Produtos demonstrativos precisam de confirmação da loja e não aceitam pagamento PIX."
            }

            var $CATEGORY1 {
              value = $PRODUCT1.Categoria|to_lower
            }

            precondition (
              ($CATEGORY1|contains:"roup") || ($CATEGORY1|contains:"vest") ||
              ($CATEGORY1|contains:"camis") || ($CATEGORY1|contains:"camisa") ||
              ($CATEGORY1|contains:"calca") || ($CATEGORY1|contains:"calça") ||
              ($CATEGORY1|contains:"saia") || ($CATEGORY1|contains:"blusa") ||
              ($CATEGORY1|contains:"casaco") || ($CATEGORY1|contains:"jaqueta") ||
              ($CATEGORY1|contains:"bermuda") || ($CATEGORY1|contains:"short") ||
              ($CATEGORY1|contains:"sueter") || ($CATEGORY1|contains:"suéter") ||
              ($CATEGORY1|contains:"moletom") || ($CATEGORY1|contains:"macacao") ||
              ($CATEGORY1|contains:"macacão") || ($CATEGORY1|contains:"lingerie") ||
              ($CATEGORY1|contains:"uniforme") || ($CATEGORY1|contains:"calcado") ||
              ($CATEGORY1|contains:"calçado") || ($CATEGORY1|contains:"sapato") ||
              ($CATEGORY1|contains:"tenis") || ($CATEGORY1|contains:"tênis") ||
              ($CATEGORY1|contains:"sandalia") || ($CATEGORY1|contains:"sandália") ||
              ($CATEGORY1|contains:"bota") || ($CATEGORY1|contains:"chinelo") ||
              ($CATEGORY1|contains:"acessorio") || ($CATEGORY1|contains:"acessório") ||
              ($CATEGORY1|contains:"bolsa") || ($CATEGORY1|contains:"cinto") ||
              ($CATEGORY1|contains:"carteira") || ($CATEGORY1|contains:"chapeu") ||
              ($CATEGORY1|contains:"chapéu") || ($CATEGORY1|contains:"bone") ||
              ($CATEGORY1|contains:"boné") || ($CATEGORY1|contains:"joia") ||
              ($CATEGORY1|contains:"jóia") || ($CATEGORY1|contains:"bijuteria")
            ) {
              error_type = "inputerror"
              error = "O catálogo contém produto fora das categorias de moda."
            }

            precondition ($PRODUCT1.Preco != null && $PRODUCT1.Preco > 0) {
              error_type = "inputerror"
              error = "Produto sem preço válido."
            }

            precondition ($PRODUCT1.Precisa_Produzir == true || $PRODUCT1.Qtd_Disp >= $LINE1.qtd) {
              error_type = "inputerror"
              error = "Estoque insuficiente para um dos produtos."
            }

            var.update $TOTAL1 {
              value = $TOTAL1 + ($PRODUCT1.Preco * $LINE1.qtd)
            }
            var.update $ITEMSNORMALIZED1 {
              value = $ITEMSNORMALIZED1|push:{
                produto_id: $PRODUCT1.id,
                qtd: $LINE1.qtd,
                preco: $PRODUCT1.Preco,
                subtotal: $PRODUCT1.Preco * $LINE1.qtd,
                precisa_produzir: $PRODUCT1.Precisa_Produzir,
                estoque_verificado: $PRODUCT1.Qtd_Disp
              }
            }
          }
        }

        precondition ($TOTAL1 > 0) {
          error_type = "inputerror"
          error = "O total calculado do pedido precisa ser maior que zero."
        }

        db.transaction {
          stack {
            db.add PEDIDO {
              enforce_hidden_fields = false
              data = {
                Total               : $TOTAL1
                cliente_id          : $CLIENTE1.id
                endereco_id         : $ENDERECO1.id
                chave_idempotencia  : $input.chave_idempotencia
                assinatura_checkout: $ASSINATURA1
                pagamento_status    : "Aguardando pagamento"
              }
            } as $CREATEDORDER1

            var.update $PEDIDO1 {
              value = $CREATEDORDER1
            }

            foreach ($ITEMSNORMALIZED1) {
              each as $NORMALIZEDITEM1 {
                db.get PRODUTO {
                  field_name = "id"
                  field_value = $NORMALIZEDITEM1.produto_id
                } as $CURRENTPRODUCT1

                precondition (
                  $CURRENTPRODUCT1 != null &&
                  $CURRENTPRODUCT1.Preco == $NORMALIZEDITEM1.preco &&
                  ($CURRENTPRODUCT1.Preco * $NORMALIZEDITEM1.qtd) == $NORMALIZEDITEM1.subtotal
                ) {
                  error_type = "inputerror"
                  error = "O catálogo mudou durante o checkout. Revise a sacola e tente novamente."
                }

                precondition (
                  $CURRENTPRODUCT1.Precisa_Produzir == true ||
                  $CURRENTPRODUCT1.Qtd_Disp >= $NORMALIZEDITEM1.qtd
                ) {
                  error_type = "inputerror"
                  error = "O estoque mudou durante o checkout. Revise a sacola e tente novamente."
                }

                db.add ITEM {
                  enforce_hidden_fields = false
                  data = {
                    pedido_id      : $CREATEDORDER1.id
                    produto_id     : $CURRENTPRODUCT1.id
                    Qtd            : $NORMALIZEDITEM1.qtd
                    Valor_Unit     : $NORMALIZEDITEM1.preco
                    Subtotal       : $NORMALIZEDITEM1.subtotal
                  }
                }

                conditional {
                  if (
                    $CURRENTPRODUCT1.Precisa_Produzir != true &&
                    $CURRENTPRODUCT1.Qtd_Disp >= $NORMALIZEDITEM1.qtd
                  ) {
                    db.patch PRODUTO {
                      field_name = "id"
                      field_value = $CURRENTPRODUCT1.id
                      data = {Qtd_Disp: $CURRENTPRODUCT1.Qtd_Disp - $NORMALIZEDITEM1.qtd}
                    }
                  }
                }
              }
            }
          }
        }
      }
    }

    api.request {
      url = "https://api-sandbox.asaas.com/v3/payments"
      method = "GET"
      params = {externalReference: $EXTERNALREFERENCE1, offset: 0, limit: 1}
      headers = [
        "access_token: " ~ $env.ASAAS_API_KEY,
        "Accept: application/json",
        "User-Agent: OSDROUPA/1.0"
      ]
      timeout = 20
    } as $EXISTINGPAYMENT1

    precondition ($EXISTINGPAYMENT1.response.status == 200) {
      error_type = "standard"
      error = "Não foi possível consultar a tentativa PIX no Asaas. Tente novamente com a mesma chave."
    }

    var $PAYMENT1 {
      value = {}
    }

    conditional {
      if (($EXISTINGPAYMENT1.response.result.data|count) > 0) {
        var.update $PAYMENT1 {
          value = $EXISTINGPAYMENT1.response.result.data.0
        }

        precondition (
          $PAYMENT1.value.customer == $ASAASCLIENTE1.Codigoclienteassas &&
          $PAYMENT1.value.value == $PEDIDO1.Total
        ) {
          error_type = "inputerror"
          error = "A tentativa PIX existente não corresponde a este pedido."
        }
      }
      else {
        api.request {
          url = "https://api-sandbox.asaas.com/v3/payments"
          method = "POST"
          params = {
            customer: $ASAASCLIENTE1.Codigoclienteassas,
            billingType: "PIX",
            value: $PEDIDO1.Total,
            dueDate: now|transform_timestamp:"+1 day"|format_timestamp:"Y-m-d":"UTC",
            description: "Pedido OSDROUPA #" ~ ($PEDIDO1.id|to_text),
            externalReference: $EXTERNALREFERENCE1
          }
          headers = [
            "access_token: " ~ $env.ASAAS_API_KEY,
            "Accept: application/json",
            "Content-Type: application/json",
            "User-Agent: OSDROUPA/1.0"
          ]
          timeout = 30
        } as $CREATEDPAYMENT1

        precondition ($CREATEDPAYMENT1.response.status == 200) {
          error_type = "standard"
          error = "O Asaas não confirmou a criação da cobrança. Tente novamente com a mesma chave."
        }

        var.update $PAYMENT1 {
          value = $CREATEDPAYMENT1.response.result
        }
      }
    }

    precondition ($PAYMENT1.value.id != null && $PAYMENT1.value.id != "") {
      error_type = "standard"
      error = "O Asaas não retornou um identificador de cobrança."
    }

    api.request {
      url = "https://api-sandbox.asaas.com/v3/payments/" ~ $PAYMENT1.value.id ~ "/pixQrCode"
      method = "GET"
      params = {}
      headers = [
        "access_token: " ~ $env.ASAAS_API_KEY,
        "Accept: application/json",
        "User-Agent: OSDROUPA/1.0"
      ]
      timeout = 20
    } as $PIX1

    precondition ($PIX1.response.status == 200) {
      error_type = "standard"
      error = "A cobrança existe, mas o Asaas ainda não retornou o QR Code. Tente novamente com a mesma chave."
    }

    precondition ($PIX1.response.result.payload != null || $PIX1.response.result.encodedImage != null) {
      error_type = "standard"
      error = "O Asaas não retornou uma instrução PIX válida."
    }

    db.get STATUS_TRANSACAO {
      field_name = "status"
      field_value = "Cobrança Criada"
    } as $PENDINGSTATUS1

    precondition ($PENDINGSTATUS1 != null) {
      error_type = "standard"
      error = "Cadastre o estado Cobrança Criada em STATUS_TRANSACAO antes de habilitar o checkout."
    }

    db.query TRANSACAO {
      where = $PEDIDO1.id == $db.TRANSACAO.pedido_id
      return = {type: "single"}
    } as $TRANSACTIONEXISTING1

    conditional {
      if ($TRANSACTIONEXISTING1 == null) {
        db.add TRANSACAO {
          enforce_hidden_fields = false
          data = {
            clienteassas       : $ASAASCLIENTE1.Codigoclienteassas
            idpayment          : $PAYMENT1.value.id
            tipo               : "PIX"
            valor              : $PEDIDO1.Total
            datavenc           : $PAYMENT1.value.dueDate
            descricao          : $PAYMENT1.value.description
            pedido_id          : $PEDIDO1.id
            status_transacao_id: $PENDINGSTATUS1.id
            status_gateway     : $PAYMENT1.value.status
            pago_confirmado    : false
          }
        } as $TRANSACTION1
      }
      else {
        precondition ($TRANSACTIONEXISTING1.idpayment == $PAYMENT1.value.id) {
          error_type = "inputerror"
          error = "O pedido já está associado a outra cobrança."
        }

        var $TRANSACTION1 {
          value = $TRANSACTIONEXISTING1
        }
      }
    }

    db.patch PEDIDO {
      field_name = "id"
      field_value = $PEDIDO1.id
      data = {pagamento_status: $PAYMENT1.value.status}
    } as $PEDIDO2
  }

  response = {
    pedido: $PEDIDO2,
    cobranca: {
      id: $PAYMENT1.value.id,
      payload: $PIX1.response.result.payload,
      encodedImage: $PIX1.response.result.encodedImage,
      expirationDate: $PIX1.response.result.expirationDate,
      status: $PAYMENT1.value.status
    }
  }
  guid = "ORDERS-OSD-2026-003"
}
