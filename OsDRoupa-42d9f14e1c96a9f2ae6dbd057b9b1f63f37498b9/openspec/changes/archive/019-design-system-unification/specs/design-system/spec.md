# Sistema visual e navegação

## Requisitos

### RF-01: Navegação pública consistente
Todas as telas que usam navegação pública devem apresentar marca, destinos comerciais e institucionais, sacola e estado da conta usando o componente compartilhado. A navegação secundária não deve comprimir os destinos na mesma faixa em telas largas.

#### Cenário: tela larga
- **Dado** que o visitante abre uma página pública em uma tela larga
- **Quando** o cabeçalho é exibido
- **Então** marca, navegação principal e ações da conta permanecem visualmente separados e legíveis

#### Cenário: tela estreita
- **Dado** que o visitante abre uma página pública em um celular
- **Quando** o cabeçalho é exibido
- **Então** a marca e as ações essenciais continuam visíveis e os demais destinos podem ser percorridos sem alargar a página

### RF-02: Linguagem visual compartilhada
Os componentes de navegação e as novas superfícies devem reutilizar paleta e fontes do projeto, oferecer foco de teclado visível e respeitar a preferência por movimento reduzido.

#### Cenário: navegação por teclado
- **Dado** que a pessoa percorre os controles usando Tab
- **Quando** um link ou botão recebe foco
- **Então** o foco tem indicação visual nítida e coerente com a paleta

#### Cenário: movimento reduzido
- **Dado** que o dispositivo solicita movimento reduzido
- **Quando** a tela renderiza
- **Então** animações decorativas e rolagem suave são reduzidas sem ocultar conteúdo

### RF-03: Página de novidades
O aplicativo deve disponibilizar `/novidades` com conteúdo editorial sobre áreas já presentes no projeto e links funcionais para elas.

#### Cenário: explorar novidades
- **Dado** que a pessoa acessa a página de novidades
- **Quando** escolhe uma área apresentada
- **Então** é encaminhada à rota correspondente, sem promessa de recurso externo indisponível
