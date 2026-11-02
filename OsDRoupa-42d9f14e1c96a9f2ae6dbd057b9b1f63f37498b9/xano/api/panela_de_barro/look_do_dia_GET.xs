// Local draft (Etapa 5 / Change 029). NÃO validado: importe, teste e publique no workspace Xano.
// Mesma regra do endpoint SQLite (professormateria/local_backend.py) e do plano B (OSDroupa/daily_look.py):
// até 4 peças limpas, uma por categoria; pontos: clima (+3 por estação) e ocasião (+2 por categoria);
// empate pela peça mais antiga. As pontuações possíveis são 5, 3, 2 e 0, por isso o laço por limiar.
// Pontos a conferir no import: filtros `to_lower`, `contains` e `in`, e os nomes das categorias no workspace.
query lookDoDia verb=GET {
  api_group = "PANELA_DE_BARRO"
  auth = "user"

  input {
    text clima?="Ameno" filters=trim|max:30
    text ocasiao?="Dia a dia" filters=trim|max:40
  }

  stack {
    db.get CLIENTE {
      field_name = "user_id"
      field_value = $auth.id
    } as $CLIENTE1

    precondition ($CLIENTE1 != null) {
      error_type = "accessdenied"
      error = "Cliente não encontrado para esta conta."
    }

    db.query ROUPA_CLIENTE {
      where = $var.CLIENTE1.id == $db.ROUPA_CLIENTE.cliente_id &&
        $db.ROUPA_CLIENTE.status != "Suja" && $db.ROUPA_CLIENTE.status != "Lavando"
      sort = {ROUPA_CLIENTE.id: "asc"}
      return = {type: "list"}
    } as $ROUPAS1

    var $CLIMA1 {
      value = $input.clima|to_lower
    }
    var $OCASIAO1 {
      value = $input.ocasiao|to_lower
    }
    var $PECAS1 {
      value = []
    }
    var $CATEGORIAS1 {
      value = []
    }
    var $ESCOLHIDAS1 {
      value = []
    }

    foreach ([5, 3, 2, 0]) {
      each as $LIMIAR1 {
        foreach ($ROUPAS1) {
          each as $ROUPA1 {
            var $ESTACAO1 {
              value = ($ROUPA1.estacao ?? "")|to_lower
            }
            var $CATEGORIA1 {
              value = ($ROUPA1.categoria ?? "")|to_lower
            }
            var $PONTOS1 {
              value = 0
            }

            conditional {
              if ($CLIMA1 == "frio" && ($ESTACAO1|contains:"inverno" || $ESTACAO1|contains:"frio")) {
                var.update $PONTOS1 {
                  value = $PONTOS1 + 3
                }
              }
            }
            conditional {
              if ($CLIMA1 == "quente" && ($ESTACAO1|contains:"verão" || $ESTACAO1|contains:"quente")) {
                var.update $PONTOS1 {
                  value = $PONTOS1 + 3
                }
              }
            }
            conditional {
              if ($OCASIAO1 == "evento" && ($CATEGORIA1|contains:"vestido" || $CATEGORIA1|contains:"acessório")) {
                var.update $PONTOS1 {
                  value = $PONTOS1 + 2
                }
              }
            }
            conditional {
              if ($OCASIAO1 == "trabalho" && ($CATEGORIA1|contains:"partes de cima" || $CATEGORIA1|contains:"partes de baixo" || $CATEGORIA1|contains:"vestido")) {
                var.update $PONTOS1 {
                  value = $PONTOS1 + 2
                }
              }
            }

            conditional {
              if (
                ($PECAS1|count) < 4 &&
                $PONTOS1 >= $LIMIAR1 &&
                ($ROUPA1.categoria|in:$CATEGORIAS1) == false &&
                ($ROUPA1.id|in:$ESCOLHIDAS1) == false
              ) {
                var.update $PECAS1 {
                  value = $PECAS1|push:$ROUPA1
                }
                var.update $CATEGORIAS1 {
                  value = $CATEGORIAS1|push:$ROUPA1.categoria
                }
                var.update $ESCOLHIDAS1 {
                  value = $ESCOLHIDAS1|push:$ROUPA1.id
                }
              }
            }
          }
        }
      }
    }
  }

  response = {clima: $input.clima, ocasiao: $input.ocasiao, pecas: $PECAS1}
  guid = "LOOK-DIA-OSD-2026-001"
}
