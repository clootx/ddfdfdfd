// Local draft (Change 028). Validate and import in the Xano workspace before publishing.
// Público: lista apenas inspirações aprovadas, sem expor autor, status ou chave.
query feedInspiracoes verb=GET {
  api_group = "PANELA_DE_BARRO"

  input {
    text ocasiao?="" filters=trim
    text clima?="" filters=trim
    text regiao?="" filters=trim
    int pagina?=1 filters=min:1
  }

  stack {
    db.query LOOK_INSPIRACAO {
      where = $db.LOOK_INSPIRACAO.status == "Publicado" &&
        ($input.ocasiao == "" || $db.LOOK_INSPIRACAO.ocasiao == $input.ocasiao) &&
        ($input.clima == "" || $db.LOOK_INSPIRACAO.clima == $input.clima) &&
        ($input.regiao == "" || $db.LOOK_INSPIRACAO.regiao == $input.regiao)
      sort = {LOOK_INSPIRACAO.created_at: "desc"}
      output = ["id", "created_at", "nome", "ocasiao", "clima", "regiao", "estacao", "paleta", "tecidos", "justificativa", "nota", "pecas", "imagem"]
      return = {
        type: "list",
        paging: {page: $input.pagina, per_page: 24, totals: false}
      }
    } as $INSPIRACOES1
  }

  response = {inspiracoes: $INSPIRACOES1.items, pagina: $input.pagina, tem_mais: $INSPIRACOES1.nextPage != null}
  guid = "FEED-OSD-2026-003"
}
