# Especificação: páginas institucionais responsivas

## Requisitos

### RF-01 — Navegação institucional

O sistema DEVE disponibilizar links para serviços, depoimentos e como funciona em desktop e dispositivos móveis.

#### Cenário: navegação em tela estreita

- Dado que a pessoa acessa o site em uma tela de até 768 px
- Quando abre a navegação institucional ou da loja
- Então os links continuam acessíveis por uma faixa horizontal rolável e o conteúdo não aumenta a largura do documento

### RF-02 — Página de serviços e alfaiataria

O sistema DEVE apresentar categorias de cuidado, ajuste e transformação de peças com chamadas para fluxos existentes.

#### Cenário: exploração de serviços

- Dado que a pessoa abre `/servicos`
- Quando percorre a página
- Então encontra serviços, orientação de processo e links para os fluxos existentes do produto

### RF-03 — Página como funciona

O sistema DEVE explicar a sequência de criação de conta, organização do armário, montagem de looks e exploração do produto.

#### Cenário: entendimento do fluxo

- Dado que a pessoa abre `/como-funciona`
- Quando percorre as etapas apresentadas
- Então consegue identificar como iniciar e quais páginas do produto usar em seguida

### RF-04 — Página de depoimentos

O sistema DEVE fornecer uma página de comunidade sem publicar falas ou avaliações inventadas como reais.

#### Cenário: ainda não há relatos publicados

- Dado que não existem depoimentos reais autorizados
- Quando a pessoa abre `/depoimentos`
- Então a página informa que está reunindo relatos e convida a pessoa a conhecer a plataforma

### RF-05 — Narrativa de rolagem acessível

O sistema DEVE revelar gradualmente as seções da home e indicar o avanço da página quando houver suporte do navegador.

#### Cenário: rolagem normal

- Dado que a pessoa navega na home em um navegador compatível
- Quando desce a página
- Então as seções entram suavemente e a barra de progresso acompanha a rolagem

#### Cenário: movimento reduzido

- Dado que o dispositivo solicita movimento reduzido ou o navegador não suporta animações ligadas à rolagem
- Quando a home é exibida
- Então todo o conteúdo continua visível sem depender da animação

### RF-06 — Responsividade

O sistema DEVE manter layout e navegação utilizáveis em 320, 390, 768 e 1280 px sem overflow horizontal involuntário.

#### Cenário: viewport móvel e desktop

- Dado que a pessoa abre uma rota institucional ou página principal em qualquer largura suportada
- Quando o layout se adapta ao viewport
- Então textos e controles cabem na tela e os grids colapsam para uma coluna quando necessário
