# Design: narrativa responsiva e páginas institucionais

## Interface

- Reutilizar os tokens `INK`, `DENIM`, `CHALK`, `THREAD`, `MUTED` e as famílias tipográficas do OSDROUPA.
- Em viewports abaixo de desktop, apresentar links em uma faixa horizontal rolável, com alvos táteis e sem ocultar acesso a login/cadastro.
- Nas páginas institucionais, alternar blocos escuros e claros, mantendo largura máxima comum, hierarquia tipográfica e grids que colapsam para uma coluna.
- Construir páginas de serviços/alfaiataria, como funciona e depoimentos, reutilizando o cabeçalho, o rodapé e o indicador de rolagem.
- No estado inicial de depoimentos, explicar que as histórias reais ainda estão sendo reunidas; não simular prova social.

## Movimento e acessibilidade

- Usar CSS Scroll-driven Animations para revelar seções e preencher uma barra de progresso quando o navegador suportar.
- Manter o conteúdo visível como fallback em navegadores sem suporte.
- Configurar rolagem suave, offset de âncora para o cabeçalho fixo e um indicador visual para continuar descendo.
- Sob `prefers-reduced-motion: reduce`, remover rolagem suave e animações de entrada/progresso.
- Evitar listeners de rolagem contínuos e transformações que causem layout shift.

## Rotas e estado

- As rotas são páginas públicas e não exigem conta.
- O cabeçalho restaura a sessão nas três novas rotas para exibir as ações coerentes com o estado da conta.
- Os CTAs apontam para fluxos já existentes (`/cadastro`, `/loja`, `/como-funciona`).
- Nenhuma entidade ou endpoint é adicionado.

## Verificação

- Importar a aplicação e gerar o build de produção.
- Abrir as três rotas e a home em viewport de 320, 390, 768 e 1280 px.
- Conferir largura do documento, erros de console, links, progressão de rolagem e comportamento com movimento reduzido.
