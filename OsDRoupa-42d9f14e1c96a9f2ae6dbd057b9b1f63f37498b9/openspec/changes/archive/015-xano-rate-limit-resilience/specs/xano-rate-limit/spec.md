# Resiliência ao limite de chamadas do Xano

## RF-XANO-LIM-01 — Enfileiramento local

Todas as chamadas do Reflex ao domínio Xano passam por um limitador compartilhado entre os processos locais, que inicia no máximo oito chamadas em qualquer janela móvel de 20 segundos. A coordenação é persistida no SQLite configurado para a aplicação.

### Cenário: Navegação rápida

- **Dado** que várias páginas ou workers iniciem chamadas ao Xano usando o mesmo SQLite
- **Quando** a janela já contiver oito chamadas iniciadas
- **Então** a próxima chamada aguarda a liberação de uma vaga

### Cenário: workers concorrentes

- **Dado** dois ou mais workers Reflex usando o mesmo arquivo SQLite
- **Quando** iniciarem chamadas ao Xano simultaneamente
- **Então** todos compartilham a mesma janela e no máximo oito chamadas iniciam em 20 segundos

## RF-XANO-LIM-02 — Resposta HTTP 429

Quando o Xano responder 429, chamadas subsequentes aguardam até 20 segundos. A chamada recusada não é repetida automaticamente, em especial quando puder criar ou alterar registros.

### Cenário: Limite compartilhado excedido

- **Dado** que outros consumidores da instância tenham usado a margem disponível
- **Quando** uma chamada da aplicação receber 429
- **Então** a interface informa a indisponibilidade temporária e orienta a aguardar
- **E** operações de escrita não são reenviadas automaticamente

## RF-XANO-LIM-03 — Reutilização da validação de sessão

Depois de validar uma sessão no Xano, as navegações do mesmo estado Reflex reutilizam os dados de conta e perfil por 60 segundos. Login, cadastro, logout ou rejeição 401/403 exigem nova validação ou encerram a sessão. Chamadas privadas continuam enviando o Bearer token ao Xano.

### Cenário: Navegação de conta autenticada

- **Dado** que o estado Reflex já validou o token e carregou o perfil
- **Quando** a pessoa navegar entre páginas da aplicação
- **Então** `/auth/me` e `buscaCliente` não são chamados novamente em cada página
- **E** endpoints privados continuam verificando o token no Xano

## RF-XANO-LIM-04 — Cache do catálogo público

A resposta pública do catálogo é mantida em memória por 60 segundos e reutilizada entre as páginas de loja e sacola no mesmo processo. O cache contém apenas dados públicos do catálogo.

### Cenário: Reabrir loja e sacola

- **Dado** que o catálogo tenha sido carregado há menos de 60 segundos
- **Quando** a pessoa abrir loja ou sacola
- **Então** a aplicação mostra os dados em cache sem repetir a chamada pública ao Xano
