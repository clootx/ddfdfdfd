# Proposta — 002-auth-landing-page

## Contexto
A versão inicial da página de autenticação do OSDroupa continha validações estáticas simuladas e um layout básico em tela única. Para transformar o sistema em um produto atraente, intuitivo e pronto para conexão com o backend Xano, é necessário redesenhar a página inicial (`/` e `/cadastro`).

A nova página inicial deve cumprir duas funções primordiais:
1. **Apresentar a marca e a proposta de valor do OSDroupa:** o conceito inovador de guarda-roupa inteligente, recomendação de looks do dia orientados ao clima/agenda e a experiência com a arara conectada (IoT).
2. **Fornecer uma experiência de autenticação impecável:** alternância fluida entre "Entrar" e "Criar Conta", validações reativas com feedback imediato, medidor de força de senha, visualização de senha, campos para dados de contato (nome, celular, CPF opcional) e integração pronta para os endpoints do Xano.

## Objetivo
Refatorar integralmente a página inicial do projeto, entregando uma interface responsiva, esteticamente refinada com design têxtil moderno, estado reativo estruturado no Reflex e contratos de autenticação robustos.

## Escopo Incluído
- Redesenho completo do componente `brand_panel` (Showcase da Marca):
  - Ilustração SVG da arara com roupas estilizadas e tag interativa climática ("22°C • Reunião").
  - Badges de valor da plataforma (Looks por IA, Arara RFID/IoT, Consumo Consciente).
- Redesenho do formulário de autenticação com abas fluidas ("Entrar" e "Criar Conta"):
  - Aba de Login: campos de e-mail e senha, "Lembrar de mim", "Esqueci a senha", feedback visual e loading state.
  - Aba de Cadastro: nome completo, e-mail, celular formatado, senha com Strength Meter visual de 4 níveis, confirmação de senha e aceite de termos.
- Tratamento de estados no Reflex (`AuthState`):
  - Validação em tempo real (regex de e-mail, requisitos de senha, correspondência de senhas).
  - Estados de carregamento (`is_loading`) para desabilitar botões durante o envio.
  - Mensagens de erro e sucesso acessíveis (`role="alert"`, `role="status"`).
  - Suporte a rotas sincronizadas: rota raiz `/` abre no modo Entrar; rota `/cadastro` abre no modo Criar Conta.
- Responsividade completa para dispositivos móveis, tablets e telas widescreen.

## Escopo Excluído
- Telas internas do dashboard do cliente (Guarda-roupa, Pedidos, Carrinho) — serão construídas nas changes subsequentes.
- Gestão de endereços e frete (Change 003).

## Dependências e Impactos
- **Frontend Reflex:** Refatoração de `OSDroupa/OSDroupa.py` mantendo compatibilidade com `rxconfig.py` e plugins Tailwind/Radix.
- **Backend Xano:** Contratos com `/auth/login`, `/auth/signup` e `cadastra_cliente` no grupo `PANELA_DE_BARRO`.
