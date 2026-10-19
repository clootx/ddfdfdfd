# Tarefas de Implementação — 002-auth-landing-page

Este checklist guia a execução das melhorias na página inicial de autenticação e cadastro.

## Fase 1 — Ajuste e Enriquecimento do Estado Reativo (`AuthState`)
- [x] 1.1 Adicionar atributos `active_tab`, `is_loading: bool = False`, `remember_me: bool = False` e `forgot_password_msg: str = ""` ao `AuthState`.
- [x] 1.2 Aprimorar o cálculo de força da senha (`strength`) com 4 requisitos claros (8+ caracteres, maiúscula, número, caractere especial).
- [x] 1.3 Implementar event handler `handle_forgot_password` para instruir o usuário sobre a recuperação de senha.
- [x] 1.4 Garantir limpeza de mensagens de erro ao digitar nos campos (`on_change`).

## Fase 2 — Redesenho do Painel de Marca (`brand_panel`)
- [x] 2.1 Refinar o SVG da arara com animação sutil de balanço e tag climática contextual ("22°C • Reunião").
- [x] 2.2 Adicionar os cards de destaque dos 3 pilares da plataforma (IA de Looks, Arara Conectada RFID e Moda Sustentável).
- [x] 2.3 Melhorar o grid de fundo e a paleta de cores têxtil (`INK`, `DENIM`, `THREAD`).

## Fase 3 — Refatoração dos Formulários de Login e Cadastro
- [x] 3.1 Melhorar o componente `mode_tabs` com transição suave entre "Entrar" e "Criar conta".
- [x] 3.2 Aprimorar o `login_form` com botão "Entrar" interativo, indicador de carregamento e link de esqueci a senha funcional.
- [x] 3.3 Aprimorar o `register_form` com medidor de força estilizado, checkbox de termos e validações automáticas de confirmação de senha.
- [x] 3.4 Estilizar os inputs com foco elegante na cor `THREAD` (`#E9A23B`) e bordas arredondadas.

## Fase 4 — Responsividade e Polimento Visual
- [x] 4.1 Ajustar o layout do container principal em grid responsivo de 2 colunas no desktop e pilha única no mobile.
- [x] 4.2 Garantir contraste visual e acessibilidade nos alertas de erro e sucesso.
- [x] 4.3 Vincular as rotas `/` e `/cadastro` no aplicativo Reflex com `on_mount` sincronizado.

## Fase 5 — Verificação e Testes
- [x] 5.1 Verificar a compilação do Reflex e ausência de erros de sintaxe em Python (`py_compile` validado com sucesso).
- [x] 5.2 Testar a alternância entre abas na mesma página e por link de rota.
- [x] 5.3 Validar os cenários BDD definidos em `specs/auth-landing.md`.
