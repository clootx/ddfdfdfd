table PRODUTO {
  auth = false

  schema {
    int id
    timestamp created_at?=now {
      visibility = "private"
    }
  
    text Nome? filters=trim
    text Descricao? filters=trim
    text Categoria? filters=trim
    text Marca? filters=trim
    text Colecao? filters=trim
    text Tipo? filters=trim
    text Tamanhos? filters=trim
    text Cores? filters=trim
    text Material? filters=trim
    text Caimento? filters=trim
    int Qtd_Disp? filters=min:0
    text Url_Imagem? filters=trim
    decimal Preco?="10.2"
    bool Precisa_Produzir?
    bool demonstracao?=false
  }

  index = [
    {type: "primary", field: [{name: "id"}]}
    {type: "btree|unique", field: [{name: "Nome", op: "desc"}]}
    {type: "btree", field: [{name: "created_at", op: "desc"}]}
  ]

  tags = ["modulo 03"]
  guid = "-VDyy2Cnyi3QlgiPLuHeI5UNk1k"
items = [
  {
    id: 900001
    Nome: "Camiseta Brisa Essencial"
    Descricao: "Produto demonstrativo criado com apoio de IA. Uma camiseta de linhas limpas para combinações do dia a dia; tecido, medidas e disponibilidade serão confirmados pela loja."
    Categoria: "Roupas"
    Qtd_Disp: 0
    Url_Imagem: ""
    Preco: 89.90
    Precisa_Produzir: true
    demonstracao: true
  },
  {
    id: 900002
    Nome: "Camisa Horizonte Leve"
    Descricao: "Produto demonstrativo criado com apoio de IA. Proposta versátil para usar aberta ou fechada em diferentes ocasiões; composição, tamanhos e prazo dependem de confirmação da loja."
    Categoria: "Roupas"
    Qtd_Disp: 0
    Url_Imagem: ""
    Preco: 149.90
    Precisa_Produzir: true
    demonstracao: true
  },
  {
    id: 900003
    Nome: "Calça Reta Aurora"
    Descricao: "Produto demonstrativo criado com apoio de IA. Silhueta reta pensada para facilitar combinações com peças básicas; medidas, tecido e disponibilidade serão confirmados pela loja."
    Categoria: "Roupas"
    Qtd_Disp: 0
    Url_Imagem: ""
    Preco: 179.90
    Precisa_Produzir: true
    demonstracao: true
  },
  {
    id: 900004
    Nome: "Vestido Solar"
    Descricao: "Produto demonstrativo criado com apoio de IA. Uma ideia de vestido leve com visual atemporal; modelagem, composição, tamanhos e prazo precisam de confirmação da loja."
    Categoria: "Roupas"
    Qtd_Disp: 0
    Url_Imagem: ""
    Preco: 189.90
    Precisa_Produzir: true
    demonstracao: true
  },
  {
    id: 900005
    Nome: "Bolsa Tiracolo Nômade"
    Descricao: "Produto demonstrativo criado com apoio de IA. Acessório compacto para acompanhar a rotina; materiais, dimensões e disponibilidade serão confirmados pela loja antes de qualquer compra."
    Categoria: "Acessórios"
    Qtd_Disp: 0
    Url_Imagem: ""
    Preco: 129.90
    Precisa_Produzir: true
    demonstracao: true
  },
  {
    id: 900006
    Nome: "Tênis Urbano Passo"
    Descricao: "Produto demonstrativo criado com apoio de IA. Proposta casual para compor looks urbanos; numeração, materiais, prazo e disponibilidade serão confirmados pela loja."
    Categoria: "Calçados"
    Qtd_Disp: 0
    Url_Imagem: ""
    Preco: 219.90
    Precisa_Produzir: true
    demonstracao: true
  },
  {
    id: 900101
    Nome: "Blazer Aurora de cintura marcada"
    Descricao: "Blazer de alfaiataria com ombros suaves, cintura levemente desenhada e fechamento frontal. Uma terceira peça polida para combinar com jeans, vestidos ou calças amplas."
    Categoria: "Roupas"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Blazer"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Chocolate, marinho, areia"
    Material: "Sarja leve de toque macio"
    Caimento: "Cintura marcada; ombro confortável"
    Qtd_Disp: 8
    Url_Imagem: "/products/blazer.svg"
    Preco: 329.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900102
    Nome: "Calça barrel utilitária Horizonte"
    Descricao: "Calça de perna curva com bolsos funcionais, cintura média e barra ajustável. A leitura utilitária ganha volume contemporâneo sem perder mobilidade."
    Categoria: "Roupas"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Calça utilitária barrel"
    Tamanhos: "34, 36, 38, 40, 42, 44, 46"
    Cores: "Oliva, cáqui, carvão"
    Material: "Sarja encorpada"
    Caimento: "Cintura média; volume curvo na perna"
    Qtd_Disp: 11
    Url_Imagem: "/products/cargo-pants.svg"
    Preco: 249.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900103
    Nome: "Saia lápis Horizonte em malha"
    Descricao: "Saia midi de linha reta com fenda posterior e cós confortável. Um desenho clássico com textura flexível para acompanhar o dia inteiro."
    Categoria: "Roupas"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Saia lápis midi"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Preto, vinho, areia"
    Material: "Malha estruturada"
    Caimento: "Ajuste confortável com fenda traseira"
    Qtd_Disp: 9
    Url_Imagem: "/products/skirt.svg"
    Preco: 179.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900104
    Nome: "Camisa ampla Risco de Giz"
    Descricao: "Camisa de botões com listras verticais, gola clássica e punhos largos. Use como peça principal, terceira camada ou amarrada na cintura."
    Categoria: "Roupas"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Camisa listrada"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Azul e branco, rosa e vinho"
    Material: "Tricoline de algodão demonstrativa"
    Caimento: "Amplo e alongado"
    Qtd_Disp: 13
    Url_Imagem: "/products/linen-shirt.svg"
    Preco: 199.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900105
    Nome: "Vestido midi Caderno de Flores"
    Descricao: "Vestido midi fluido com cintura baixa suave e estampa floral retrô. As mangas leves e a barra em movimento criam uma peça expressiva para o dia ou a noite."
    Categoria: "Roupas"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Vestido midi estampado"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Creme floral, azul floral"
    Material: "Viscose leve demonstrativa"
    Caimento: "Solto com faixa removível"
    Qtd_Disp: 6
    Url_Imagem: "/products/midi-dress.svg"
    Preco: 289.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900106
    Nome: "Jaqueta curta Fecho de Sapo"
    Descricao: "Jaqueta curta de gola alta com fechamento ornamental e acabamento contrastante. Uma camada estruturada que dá foco ao look sem limitar os movimentos."
    Categoria: "Roupas"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Jaqueta curta"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Azul-noite, telha, preto"
    Material: "Sarja de algodão demonstrativa"
    Caimento: "Curto e levemente ajustado"
    Qtd_Disp: 7
    Url_Imagem: "/products/blazer.svg"
    Preco: 279.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900107
    Nome: "Camiseta gráfica Rua em Movimento"
    Descricao: "Camiseta de shape amplo com arte original da boutique fictícia, gola reforçada e ombro deslocado. Uma base streetwear para misturar com peças clássicas."
    Categoria: "Roupas"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Camiseta oversized"
    Tamanhos: "PP, P, M, G, GG, XG, 2XG"
    Cores: "Branco, preto, verde-lima"
    Material: "Malha de algodão demonstrativa"
    Caimento: "Oversized unissex"
    Qtd_Disp: 20
    Url_Imagem: "/products/streetwear-tee.svg"
    Preco: 99.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900108
    Nome: "Jeans perna ampla Céu de Concreto"
    Descricao: "Jeans de lavagem média, cintura confortável e perna ampla. O desenho reto a partir do quadril combina com tênis, mocassim ou salto."
    Categoria: "Roupas"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Jeans wide leg"
    Tamanhos: "34, 36, 38, 40, 42, 44, 46, 48"
    Cores: "Índigo médio, preto lavado"
    Material: "Denim demonstrativo"
    Caimento: "Cintura média; perna ampla"
    Qtd_Disp: 14
    Url_Imagem: "/products/tailored-trousers.svg"
    Preco: 219.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900109
    Nome: "Bermuda de alfaiataria Quadra"
    Descricao: "Bermuda alongada com pregas frontais e bolsos laterais. A construção de alfaiataria deixa a peça pronta para composições casuais ou arrumadas."
    Categoria: "Roupas"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Bermuda"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Carvão, areia, vermelho tomate"
    Material: "Tecido plano leve"
    Caimento: "Cintura média; comprimento no joelho"
    Qtd_Disp: 10
    Url_Imagem: "/products/tailored-trousers.svg"
    Preco: 169.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900110
    Nome: "Jaqueta bomber Clube do Bairro"
    Descricao: "Bomber com gola, punhos e barra em ribana, bolsos frontais e corpo leve. A referência esportiva foi desenhada para sobreposições urbanas."
    Categoria: "Roupas"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Jaqueta bomber"
    Tamanhos: "PP, P, M, G, GG, XG, 2XG"
    Cores: "Marinho e creme, verde e vinho"
    Material: "Sarja leve com acabamento em malha"
    Caimento: "Amplo; comprimento no quadril"
    Qtd_Disp: 5
    Url_Imagem: "/products/blazer.svg"
    Preco: 299.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900111
    Nome: "Colete utilitário Mapa Aberto"
    Descricao: "Colete sem mangas com bolsos aplicados e ajuste lateral. Uma sobreposição funcional para carregar itens pequenos e criar camadas em dias amenos."
    Categoria: "Roupas"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Colete utilitário"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Oliva, areia, preto"
    Material: "Sarja leve"
    Caimento: "Reto com regulagem lateral"
    Qtd_Disp: 8
    Url_Imagem: "/products/blazer.svg"
    Preco: 189.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900112
    Nome: "Boné aba curva Ponto de Encontro"
    Descricao: "Boné de seis painéis com aba curva, regulagem posterior e bordado abstrato exclusivo da marca de demonstração."
    Categoria: "Acessórios"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Boné"
    Tamanhos: "Ajustável"
    Cores: "Azul, vermelho, cáqui"
    Material: "Sarja demonstrativa"
    Caimento: "Fecho ajustável"
    Qtd_Disp: 18
    Url_Imagem: "/products/cap.svg"
    Preco: 79.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900113
    Nome: "Top transpassado Nó de Maré"
    Descricao: "Top transpassado com amarração ajustável e decote suave. Pode ser usado como blusa ou sobreposição em vestido e regata."
    Categoria: "Roupas"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Top transpassado"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Azul-claro, coral, creme"
    Material: "Viscose leve demonstrativa"
    Caimento: "Ajustável por amarração"
    Qtd_Disp: 9
    Url_Imagem: "/products/linen-shirt.svg"
    Preco: 139.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900114
    Nome: "Conjunto Praia Janela Aberta"
    Descricao: "Conjunto demonstrativo de camisa ampla e short com cós elástico. Peças independentes para montar combinações de resort, cidade ou fim de semana."
    Categoria: "Roupas"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Conjunto camisa e short"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Listra azul, listra terracota"
    Material: "Tecido leve de aspecto natural"
    Caimento: "Camisa ampla; short ajustável"
    Qtd_Disp: 6
    Url_Imagem: "/products/linen-shirt.svg"
    Preco: 279.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900115
    Nome: "Blusa lenço Brisa Gráfica"
    Descricao: "Blusa de alças com detalhe frontal drapeado como um lenço. A estampa geométrica funciona como ponto de cor em looks neutros."
    Categoria: "Roupas"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Blusa lenço"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Azul e areia, verde e coral"
    Material: "Crepe leve demonstrativo"
    Caimento: "Solto com alças ajustáveis"
    Qtd_Disp: 8
    Url_Imagem: "/products/cotton-scarf.svg"
    Preco: 159.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900116
    Nome: "Saia longa Franja de Sol"
    Descricao: "Saia longa com movimento e acabamento de franjas discretas na barra. A cintura ajustável e o tecido fluido trazem textura às produções."
    Categoria: "Roupas"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Saia longa texturizada"
    Tamanhos: "PP, P, M, G, GG, XG"
    Cores: "Cru, azul profundo, terracota"
    Material: "Tecido fluido demonstrativo"
    Caimento: "Cintura confortável; movimento amplo"
    Qtd_Disp: 7
    Url_Imagem: "/products/skirt.svg"
    Preco: 229.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900117
    Nome: "Maiô inteiro Linha d'Água"
    Descricao: "Maiô demonstrativo com alças reguláveis, decote reto e forro. Também pode compor looks urbanos como body."
    Categoria: "Roupas"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Maiô"
    Tamanhos: "P, M, G, GG, XG"
    Cores: "Azul-piscina, preto, vermelho"
    Material: "Malha de praia demonstrativa"
    Caimento: "Alças ajustáveis; forro frontal"
    Qtd_Disp: 7
    Url_Imagem: "/products/swimwear.svg"
    Preco: 189.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900118
    Nome: "Bolsa tote Mercado de Domingo"
    Descricao: "Tote espaçosa com bolso interno e alças confortáveis para os itens essenciais do dia, compras leves ou uma troca de roupa."
    Categoria: "Acessórios"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Bolsa tote"
    Tamanhos: "Único"
    Cores: "Cru, azul, listrada"
    Material: "Lona demonstrativa"
    Caimento: "Alças de ombro"
    Qtd_Disp: 12
    Url_Imagem: "/products/tote.svg"
    Preco: 129.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900119
    Nome: "Legging de treino Ritmo Livre"
    Descricao: "Legging de cintura alta, bolso lateral e costuras planas. Modelagem demonstrativa para treino leve, caminhada e rotina ativa."
    Categoria: "Roupas"
    Marca: "Forma Livre"
    Colecao: "Corpo em movimento"
    Tipo: "Legging"
    Tamanhos: "PP, P, M, G, GG, XG, 2XG"
    Cores: "Preto, uva, azul elétrico"
    Material: "Malha elástica demonstrativa"
    Caimento: "Cintura alta; compressão leve"
    Qtd_Disp: 10
    Url_Imagem: "/products/activewear.svg"
    Preco: 169.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900120
    Nome: "Top esportivo Pulso Duplo"
    Descricao: "Top de alças largas com forro removível e suporte leve a médio. Uma base confortável para treino de baixo impacto e composições esportivas."
    Categoria: "Roupas"
    Marca: "Forma Livre"
    Colecao: "Corpo em movimento"
    Tipo: "Top esportivo"
    Tamanhos: "PP, P, M, G, GG, XG, 2XG"
    Cores: "Preto, azul, coral"
    Material: "Malha elástica demonstrativa"
    Caimento: "Alças largas; suporte leve a médio"
    Qtd_Disp: 11
    Url_Imagem: "/products/activewear.svg"
    Preco: 119.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900121
    Nome: "Jaqueta corta-vento Vento de Rua"
    Descricao: "Corta-vento leve com capuz ajustável, fechamento frontal e bolsos com zíper. Dobrável para passeios e atividades ao ar livre."
    Categoria: "Roupas"
    Marca: "Forma Livre"
    Colecao: "Corpo em movimento"
    Tipo: "Jaqueta esportiva"
    Tamanhos: "PP, P, M, G, GG, XG, 2XG"
    Cores: "Azul elétrico, lima, preto"
    Material: "Tecido leve demonstrativo"
    Caimento: "Reto com capuz ajustável"
    Qtd_Disp: 6
    Url_Imagem: "/products/knitwear.svg"
    Preco: 239.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900122
    Nome: "Polo piquet Jogo Aberto"
    Descricao: "Polo de manga curta com gola contrastante e aberturas laterais. A referência esportiva ganha cores vivas para entrar no cotidiano."
    Categoria: "Roupas"
    Marca: "Forma Livre"
    Colecao: "Corpo em movimento"
    Tipo: "Polo"
    Tamanhos: "PP, P, M, G, GG, XG, 2XG"
    Cores: "Branco e azul, vinho e rosa, preto e lima"
    Material: "Malha piquet demonstrativa"
    Caimento: "Reto e confortável"
    Qtd_Disp: 9
    Url_Imagem: "/products/linen-shirt.svg"
    Preco: 149.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900123
    Nome: "Tênis de lona Passo a Passo"
    Descricao: "Tênis baixo de amarração, cabedal de lona e sola flexível. Uma opção versátil para peças amplas e conjuntos esportivos demonstrativos."
    Categoria: "Calçados"
    Marca: "Forma Livre"
    Colecao: "Corpo em movimento"
    Tipo: "Tênis casual"
    Tamanhos: "34 a 43"
    Cores: "Branco, preto, azul"
    Material: "Lona e sola flexível demonstrativas"
    Caimento: "Forma casual; cadarço ajustável"
    Qtd_Disp: 10
    Url_Imagem: "/products/canvas-sneakers.svg"
    Preco: 199.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900124
    Nome: "Mocassim bicolor Ponto Firme"
    Descricao: "Mocassim de perfil clássico com recorte bicolor, palmilha macia demonstrativa e sola baixa. Um contraste gráfico para alfaiataria ou denim."
    Categoria: "Calçados"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Mocassim bicolor"
    Tamanhos: "34 a 41"
    Cores: "Creme e preto, vinho e rosa"
    Material: "Material sintético demonstrativo"
    Caimento: "Bico arredondado; sola baixa"
    Qtd_Disp: 5
    Url_Imagem: "/products/loafer.svg"
    Preco: 229.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900125
    Nome: "Sandália de tiras Caminho de Sal"
    Descricao: "Sandália rasteira com tiras ajustáveis e palmilha plana para acompanhar vestidos, conjuntos leves e peças de praia."
    Categoria: "Calçados"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Sandália rasteira"
    Tamanhos: "34 a 40"
    Cores: "Caramelo, preto, dourado fosco"
    Material: "Material sintético demonstrativo"
    Caimento: "Tiras ajustáveis; sola plana"
    Qtd_Disp: 8
    Url_Imagem: "/products/sandal.svg"
    Preco: 149.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900126
    Nome: "Cinto largo Fio de Prumo"
    Descricao: "Cinto largo com fivela geométrica e ajuste por múltiplos furos. Acessório de destaque para marcar a cintura sobre vestido, blazer ou camisa longa."
    Categoria: "Acessórios"
    Marca: "Ateliê Entrelinhas"
    Colecao: "Alfaiataria expressiva"
    Tipo: "Cinto"
    Tamanhos: "P, M, G, GG"
    Cores: "Caramelo, vinho, preto"
    Material: "Material sintético demonstrativo"
    Caimento: "Ajuste por múltiplos furos"
    Qtd_Disp: 14
    Url_Imagem: "/products/caramel-belt.svg"
    Preco: 89.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900127
    Nome: "Lenço estampado Cartografia"
    Descricao: "Lenço quadrado com estampa original inspirada em mapas e arquitetura. Pode ser usado no pescoço, cabelo, como faixa ou amarrado à bolsa."
    Categoria: "Acessórios"
    Marca: "Maré de Dentro"
    Colecao: "Verão sem pressa"
    Tipo: "Lenço"
    Tamanhos: "Único · 70 × 70 cm"
    Cores: "Azul e terracota, verde e creme"
    Material: "Tecido leve demonstrativo"
    Caimento: "Quadrado; múltiplas amarrações"
    Qtd_Disp: 16
    Url_Imagem: "/products/cotton-scarf.svg"
    Preco: 69.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900128
    Nome: "Bolsa transversal Pista Livre"
    Descricao: "Bolsa compacta com alça regulável, bolso frontal e fechamento seguro para telefone, carteira e pequenos essenciais."
    Categoria: "Acessórios"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Bolsa transversal"
    Tamanhos: "Único"
    Cores: "Preto, verde, lilás"
    Material: "Lona resistente demonstrativa"
    Caimento: "Alça transversal ajustável"
    Qtd_Disp: 10
    Url_Imagem: "/products/crossbody-bag.svg"
    Preco: 119.00
    Precisa_Produzir: false
    demonstracao: true
  },
  {
    id: 900129
    Nome: "Óculos geométrico Prisma Solar"
    Descricao: "Armação geométrica demonstrativa com lentes escuras. Um acessório de estilo para looks urbanos e composições de verão."
    Categoria: "Acessórios"
    Marca: "Rua Viva Studio"
    Colecao: "Cidade em camadas"
    Tipo: "Óculos de sol"
    Tamanhos: "Único"
    Cores: "Preto, âmbar, vermelho"
    Material: "Armação demonstrativa"
    Caimento: "Hastes com apoio confortável"
    Qtd_Disp: 8
    Url_Imagem: "/products/sunglasses.svg"
    Preco: 99.00
    Precisa_Produzir: false
    demonstracao: true
  }
]
}
