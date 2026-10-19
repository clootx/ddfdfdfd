# Especificação — Conteúdo e Desafios

## RF-CONT-01: Conteúdo editorial

Visitante pode navegar inspiração, artigos e detalhe por slug; páginas não apresentam conteúdo enviado por outra pessoa como se fosse real.

## RF-CONT-02: Desafios pessoais

Conta validada pode ver desafios e marcar conclusão. O progresso é isolado por ID de conta no armazenamento local.

### Cenário: sessão ausente
- **Dado** que não existe JWT válido
- **Quando** a pessoa abre `/desafios`
- **Então** é encaminhada para `/login` sem ver progresso de outra conta

## RF-CONT-03: Transparência de sincronização

Enquanto o progresso não estiver no backend, a interface informa que ele está salvo somente neste navegador.

## RF-CONT-04: Conteúdo não encontrado

Slug de artigo desconhecido exibe estado de não encontrado e link para a coleção.
