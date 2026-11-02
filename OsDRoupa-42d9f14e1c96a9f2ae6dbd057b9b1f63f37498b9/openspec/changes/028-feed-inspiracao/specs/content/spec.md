# Especificação — Feed de inspirações (delta de `content`)

## Requisitos Funcionais

### RF-CONT-01 (alterado) — Conteúdo editorial e feed
Visitantes podem navegar as ideias editoriais e o feed público de inspirações em `/inspiracao`. O feed lista somente inspirações aprovadas, da mais recente para a mais antiga, 24 por página, sem identificar quem publicou.

### RF-FEED-01 — Guardar inspiração
Pessoa autenticada pode guardar uma proposta da IA como inspiração privada. A operação é idempotente pela chave da proposta, e uma chave usada por outra conta é recusada.

### RF-FEED-02 — Privacidade das peças
Fotos do armário nunca são gravadas na inspiração. Só imagens do catálogo (caminho local ou HTTPS) e a imagem gerada por IA (caminho `looks/<hex32>.png|jpg|webp`) são aceitas. Qualquer outra referência é descartada ou recusada no servidor.

### RF-FEED-03 — Filtros
O feed pode ser filtrado por ocasião, clima (Quente, Ameno, Frio, Chuvoso) e região do Brasil. Um filtro fora dos valores permitidos é recusado.

### RF-FEED-04 — Salvos
Pessoa autenticada pode salvar e remover dos salvos inspirações publicadas; salvar duas vezes não duplica. Inspirações não publicadas não podem ser salvas.

### RF-FEED-05 — Publicação moderada
A dona da inspiração pode enviá-la ao feed com autorização explícita de publicação anônima. O status passa de Privado ou Recusado para Pendente. Apenas administradores aprovam (Publicado) ou recusam (Recusado).

### RF-FEED-06 — Exclusão
A dona pode excluir a inspiração em qualquer status; ela sai do feed e dos salvos de todas as pessoas.

---

## Cenários de Aceitação (Gherkin BDD)

### Cenário 1: guardar e ver em Minhas inspirações
- **Dado** uma proposta da IA com imagem gerada,
- **Quando** a pessoa clica em "Guardar inspiração",
- **Então** a inspiração aparece em "Minhas inspirações" como "Só para você", com a imagem e a nota.

### Cenário 2: foto do armário não vaza
- **Dado** uma proposta com uma peça do armário cuja foto foi enviada por upload,
- **Quando** ela é guardada e publicada,
- **Então** nenhuma resposta da API contém a foto da peça.

### Cenário 3: publicação exige consentimento e moderação
- **Dado** uma inspiração privada,
- **Quando** a pessoa autoriza o envio ao feed,
- **Então** o status vira "Em revisão" e a inspiração não aparece no feed até um administrador publicá-la.

### Cenário 4: filtros
- **Dado** inspirações publicadas do Nordeste e do Sul,
- **Quando** a pessoa filtra por região "Sul",
- **Então** vê apenas as do Sul.

### Cenário 5: salvar do feed
- **Dado** uma inspiração publicada por outra pessoa,
- **Quando** a pessoa clica em "Salvar",
- **Então** ela aparece em "Salvas do feed" e o botão mostra "Salva".

### Cenário 6: acesso indevido
- **Dado** uma conta sem papel admin,
- **Quando** acessa `/gestao/inspiracoes`,
- **Então** recebe a mensagem de acesso restrito e nenhuma inspiração pendente é exibida.
