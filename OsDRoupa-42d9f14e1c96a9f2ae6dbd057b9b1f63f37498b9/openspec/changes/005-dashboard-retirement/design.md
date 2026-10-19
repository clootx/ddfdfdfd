# Design — 005-dashboard-retirement

## Decisões

- Reutilizar o destino comum `HOME_AFTER_AUTH = "/#como-funciona"` após login e cadastro.
- Manter o estado de autenticação, o token JWT e as validações atuais sem alterações.
- Remover o componente de página do dashboard e seu registro de rota somente durante a aplicação aprovada desta change.
- Substituir referências de navegação “Painel” que apontem para `/dashboard` por “Início”, apontando para `/`.
- Não criar uma nova página nem alterar o backend Xano.

## Arquivos e Superfícies Impactados

| Arquivo / área | Mudança proposta |
|---|---|
| `OSDroupa/OSDroupa.py` | Remover a página e helpers exclusivos do dashboard, desregistrar `/dashboard` e atualizar links internos |
| `openspec/specs/auth/spec.md` | Manter o comportamento canônico de redirecionamento pós-autenticação para `/#como-funciona` |
| `openspec/changes/README.md` | Atualizar o status da Change 005 após sua conclusão |

## Compatibilidade

A remoção de `/dashboard` é uma mudança de navegação intencional. Após login ou cadastro, o usuário continua autenticado, mas passa a chegar à seção pública “Como funciona”. As demais rotas e chamadas protegidas não devem perder seus controles de autenticação.

## Verificação

- Confirmar que login e cadastro bem-sucedidos navegam para `/#como-funciona`.
- Confirmar que nenhuma página ou link da aplicação ainda aponta para `/dashboard`.
- Confirmar que `/dashboard` deixa de renderizar o painel.
- Compilar o módulo Reflex e validar que as páginas remanescentes continuam registradas.
