# Proposta — 030-perfil-estilo-ia

## Por quê
O estilista (Changes 025 e 029) trata todas as pessoas do mesmo jeito: não sabe quais cores ela prefere, quais peças estão paradas no armário nem quais sugestões ela rejeitou. Sem isso, os looks se repetem e ignoram o gosto pessoal.

## O que muda
- **Perfil de estilo para a IA:** estilo preferido, cores favoritas, peças mais e menos usadas (do histórico de uso) e resumo do feedback, enviados só como chaves de peças, cores e motivos.
- **Feedback 👍/👎** em cada look da IA; 👎 pede um motivo de uma lista fechada. Gravado **apenas** quando a pessoa clica.
- **Opção de desligar** a personalização no perfil (ligada por padrão) e botão para **apagar** o histórico de avaliações.
- Texto de privacidade atualizado.

## Fora do escopo
- Tamanhos não são enviados à IA (não ajudam a combinar peças do próprio armário).
- Aprendizado automático além do resumo enviado no prompt.

## Impacto
SQLite: tabela `look_feedback`, coluna `users.ai_personalization`, endpoint `feedbackLooks` (GET/POST/DELETE) e campo `personalizacao_ia` em `buscaCliente`/`perfil`. Xano: rascunhos equivalentes, não publicados.
