# Design técnico: sistema visual unificado

## Interface Reflex

- `site_navbar()` será a fonte compartilhada para os cabeçalhos de marketing e loja. A faixa superior reúne marca, quatro destinos principais, sacola e ação da conta. A faixa inferior reúne páginas institucionais e, quando autenticada, ferramentas pessoais. No celular, as faixas preservam a hierarquia e a navegação secundária rola horizontalmente.
- `home_navbar()` e `store_navbar()` continuam como funções de compatibilidade e delegam ao componente compartilhado. A gestão conserva os destinos administrativos, com o mesmo estilo de superfície e comportamento adaptável.
- A página `/novidades` será montada com os componentes Reflex existentes e mostrará apenas áreas encontradas no aplicativo: armário digital, looks e agenda, alfaiataria/serviços, inspiração/desafios e catálogo.
- O rodapé das páginas institucionais recebe link para novidades. A rota usa o carregamento de sessão já aplicado às demais páginas públicas.

## Tokens e movimento

- Usar `INK`, `DENIM`, `CHALK`, `THREAD`, `MUTED` e as fontes `Bricolage Grotesque` e `Figtree` já carregadas; evitar uma paleta paralela.
- CSS global define foco visível, seleção, superfícies, estados de hover e utilitários de entrada. Animações respeitam `prefers-reduced-motion`; nenhuma ação depende de animação.
- Não introduzir biblioteca de animação ou ícones adicional: os ícones Lucide via `rx.icon` e o CSS existente mantêm o pacote leve.

## Compatibilidade e dados

- Não muda contratos de estado, backend, banco ou endpoints. Links preservam as rotas existentes e a nova rota é pública.
- A vitrine editorial não simula lançamentos comerciais nem avaliações; links levam às funcionalidades disponíveis.
