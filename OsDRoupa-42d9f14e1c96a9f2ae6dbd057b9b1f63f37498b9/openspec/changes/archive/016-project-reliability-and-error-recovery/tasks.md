# Tarefas

> A recuperação local sem SMTP foi implementada na Change 017 com link de uso único. As tarefas abertas abaixo tratam da alternativa por e-mail e da validação específica no Xano.

- [x] 1.1 Documentar os defeitos observados e os limites externos de configuração.
- [x] 1.2 Respeitar `Retry-After` numérico e em data HTTP, mantendo a fila local de chamadas.
- [x] 1.3 Mostrar erros de limite nos fluxos de autenticação, catálogo, checkout e pedidos.
- [x] 1.4 Separar sessão expirada de validação temporariamente indisponível e de `403` de recurso.
- [x] 1.5 Implementar a escolha entre cookie de sessão e cookie persistente de 24 horas.
- [x] 1.6 Remover a confirmação falsa de recuperação e impedir que o app chame o endpoint de e-mail de demonstração.
- [x] 1.7 Atualizar os documentos de contexto e o índice OpenSpec para refletir a estrutura atual.
- [x] 1.8 Ocultar o selo padrão do Reflex para manter a identidade visual da aplicação em produção.
- [x] 1.9 Executar o build de produção do React Router em cópia isolada e confirmar serviço HTTP das principais rotas.
- [x] 1.10 Exercitar no Chrome o login inválido, cadastro, recuperação e redefinição local de senha, redirecionamento pós-cadastro, sessão após recarga do perfil e layout móvel.
- [x] 1.11 Limpar senhas e campos de cadastro após validar a nova sessão.
- [ ] 2.1 Validar o XanoScript alterado em sandbox ou prévia de importação suportada.
- [ ] 2.2 Implementar e exercitar recuperação com envio SendGrid ao próprio usuário, resposta sem enumeração e uma conta de teste.
- [ ] 2.3 Exercitar sessão persistente, cookie de sessão, `429`, `403` de recurso e nova tentativa no navegador.
- [ ] 2.4 Publicar apenas depois de revisar uma prévia válida do workspace de destino.
