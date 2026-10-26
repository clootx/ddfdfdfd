query checkoutPedidoDemonstrativo verb=POST {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    int endereco_id? filters=min:1
    json itens
    text chave_idempotencia filters=trim|min:16|max:80
  }

  stack {
    precondition (($input.itens|count) >= 1 && ($input.itens|count) <= 20) {
      error_type = "inputerror"
      error = "O pedido precisa conter de 1 a 20 produtos."
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

    var $CHAVE1 {
      value = "DEMO-" ~ $input.chave_idempotencia
    }

    var $ASSINATURA1 {
      value = {metodo: "DEMONSTRATIVO", endereco_id: $input.endereco_id, itens: $input.itens}|json_encode
    }

    db.query PEDIDO {
      where = $CLIENTE1.id == $db.PEDIDO.cliente_id && $CHAVE1 == $db.PEDIDO.chave_idempotencia
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

    conditional {
      if ($EXISTINGORDER1 != null) {
        precondition (
          $EXISTINGORDER1.endereco_id == $input.endereco_id &&
          $EXISTINGORDER1.assinatura_checkout == $ASSINATURA1 &&
          $EXISTINGORDER1.pagamento_status == "Aguardando confirmação da loja"
        ) {
          error_type = "inputerror"
          error = "A chave de idempotência já foi usada para outro pedido."
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
            precondition ($LINE1.produto_id != null && $LINE1.qtd >= 1 && $LINE1.qtd <= 99) {
              error_type = "inputerror"
              error = "Cada item precisa ter um produto e quantidade entre 1 e 99."
            }

            db.get PRODUTO {
              field_name = "id"
              field_value = $LINE1.produto_id
            } as $PRODUCT1

            precondition (
              $PRODUCT1 != null && $PRODUCT1.demonstracao == true &&
              $PRODUCT1.Precisa_Produzir == true
            ) {
              error_type = "inputerror"
              error = "Este checkout aceita somente produtos demonstrativos sob encomenda."
            }

            precondition (
              $PRODUCT1.Categoria == "Roupas" ||
              $PRODUCT1.Categoria == "Calçados" ||
              $PRODUCT1.Categoria == "Acessórios"
            ) {
              error_type = "inputerror"
              error = "O pedido contém um produto fora das categorias de moda."
            }

            precondition ($PRODUCT1.Preco != null && $PRODUCT1.Preco > 0) {
              error_type = "inputerror"
              error = "Produto sem preço válido."
            }

            var.update $TOTAL1 {
              value = $TOTAL1 + ($PRODUCT1.Preco * $LINE1.qtd)
            }
            var.update $ITEMSNORMALIZED1 {
              value = $ITEMSNORMALIZED1|push:{
                produto_id: $PRODUCT1.id,
                qtd: $LINE1.qtd,
                preco: $PRODUCT1.Preco,
                subtotal: $PRODUCT1.Preco * $LINE1.qtd
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
                chave_idempotencia  : $CHAVE1
                assinatura_checkout: $ASSINATURA1
                pagamento_status    : "Aguardando confirmação da loja"
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
                  $CURRENTPRODUCT1.demonstracao == true &&
                  $CURRENTPRODUCT1.Precisa_Produzir == true &&
                  $CURRENTPRODUCT1.Preco == $NORMALIZEDITEM1.preco
                ) {
                  error_type = "inputerror"
                  error = "O catálogo mudou durante o checkout. Revise a sacola e tente novamente."
                }

                db.add ITEM {
                  enforce_hidden_fields = false
                  data = {
                    pedido_id  : $CREATEDORDER1.id
                    produto_id : $CURRENTPRODUCT1.id
                    Qtd        : $NORMALIZEDITEM1.qtd
                    Valor_Unit : $NORMALIZEDITEM1.preco
                    Subtotal   : $NORMALIZEDITEM1.subtotal
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  response = {
    pedido: $PEDIDO1,
    total: $TOTAL1,
    pagamento_status: "Aguardando confirmação da loja",
    pagamento_realizado: false
  }
  guid = "ORDERS-OSD-2026-014"
}
