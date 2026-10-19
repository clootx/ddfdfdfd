# Especificação — Nova Página Inicial (Cadastro e Entrar)

## Requisitos Funcionais

### RF-PAGE-01: Navegação entre Modos de Acesso
O usuário deve poder alternar facilmente entre o modo "Entrar" e "Criar conta" através de abas (tabs) no formulário, sem que ocorra perda do contexto visual da página.
- A rota `/` deve carregar por padrão o modo "Entrar".
- A rota `/cadastro` deve carregar por padrão o modo "Criar conta".

### RF-PAGE-02: Painel de Marca e Proposta de Valor
A página deve exibir à esquerda (ou no topo em dispositivos móveis) um painel visual da marca OSDroupa contendo:
- Logo com gancho de cabide estilizado e tipografia expressiva.
- Slogan principal: "Abra o armário já sabendo o que vestir."
- Ilustração animada em SVG de uma arara com cabides e tag de look com temperatura e ocasião.
- Três pilares do ecossistema:
  1. *Look do Dia com IA*: combina clima e agenda pessoal.
  2. *Arara Inteligente*: integração física com RFID e LEDs pick-to-light.
  3. *Moda Sustentável*: uso inteligente e peças sob demanda.

### RF-PAGE-03: Formulário de Login (Entrar)
O formulário de login deve conter:
- Campo de e-mail com validação de formato.
- Campo de senha com alternador de visibilidade (ícone de olho).
- Checkbox de "Manter conectado".
- Link de recuperação "Esqueci minha senha" com feedback visual ao clicar.
- Botão "Entrar" com estilo têxtil pontilhado ("stitched button") e estado de carregamento.

### RF-PAGE-04: Formulário de Cadastro (Criar Conta)
O formulário de cadastro deve solicitar:
- Nome completo (validação de ao menos 2 palavras: nome e sobrenome).
- E-mail com validação em tempo real.
- Celular com formato nacional.
- Senha com requisitos de segurança:
  - Mínimo de 8 caracteres.
  - Pelo menos uma letra maiúscula.
  - Pelo menos um número.
  - Pelo menos um caractere especial.
- Medidor visual de força da senha com 4 barras e legendas contextuais (Fraca, Razoável, Boa, Forte).
- Campo de confirmação de senha com validação de correspondência.
- Checkbox obrigatório de consentimento com os termos de uso.

### RF-PAGE-05: Feedback e Tratamento de Erros
- Mensagens de erro devem ser exibidas em tom de alerta visual com contraste adequado (`role="alert"`).
- Mensagens de sucesso devem destacar o avanço do usuário (`role="status"`).
- O botão de ação deve ser desabilitado durante o processamento para prevenir cliques duplicados.

---

## Cenários de Aceitação (Gherkin BDD)

### Cenário 1: Login com credenciais válidas
- **Dado** que o usuário está na aba "Entrar",
- **Quando** informa seu e-mail cadastrado e senha correta (>= 8 caracteres) e clica em "Entrar",
- **Então** o sistema exibe estado de carregamento e confirma a autenticação com mensagem de sucesso.

### Cenário 2: Tentativa de login com e-mail inválido
- **Dado** que o usuário digita "usuario@invalido" (sem domínio completo),
- **Quando** submete o formulário de login,
- **Então** o sistema exibe o alerta: "Digite um e-mail válido." e mantém o foco no formulário.

### Cenário 3: Avaliação de força de senha no cadastro
- **Dado** que o usuário está no campo de criação de senha,
- **Quando** digita apenas 4 letras minúsculas (ex.: "roup"),
- **Então** o medidor exibe 1 barra e a legenda "Fraca".
- **Quando** o usuário acrescenta maiúscula, número e símbolo (ex.: "Roupas#2026"),
- **Então** o medidor preenche as 4 barras com a legenda "Forte".

### Cenário 4: Senhas não correspondentes no cadastro
- **Dado** que o usuário digitou uma senha forte no primeiro campo,
- **Quando** digita uma senha diferente no campo "Confirmar senha" e clica em "Criar conta",
- **Então** o sistema bloqueia o envio e exibe: "As senhas não conferem."

### Cenário 5: Alternância de visibilidade da senha
- **Dado** que o usuário digitou sua senha mascarada ("••••••••"),
- **Quando** clica no ícone de visualização (olho),
- **Então** os caracteres da senha tornam-se legíveis e o ícone alterna para olho riscado.
