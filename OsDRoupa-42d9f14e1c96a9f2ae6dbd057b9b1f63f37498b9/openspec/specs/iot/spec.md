# Especificação consolidada — Armário Inteligente e IoT

## RF-IOT-01: Dispositivos privados
Uma conta autenticada consulta apenas dispositivos associados ao cliente derivado da sessão Xano.

### Cenário: listar dispositivos da conta atual
- **Dado** que a sessão Xano da conta é válida
- **Quando** a pessoa abre `/dispositivos`
- **Então** a página mostra somente dispositivos vinculados ao cliente dessa sessão

### Cenário: impedir acesso sem sessão válida
- **Dado** que não há sessão válida
- **Quando** a pessoa abre uma página de dispositivo
- **Então** a navegação retorna para `/login` sem consultar dados privados

## RF-IOT-02: Pareamento
O servidor emite um código curto, expirável e de uso único, associado à conta que iniciou o processo. Confirmar pareamento vincula o dispositivo a essa conta.

### Cenário: solicitar código de pareamento
- **Dado** que a conta autenticada informa o identificador de um dispositivo compatível
- **Quando** o serviço de pareamento está disponível
- **Então** o servidor emite um código temporário e informa quando ele expira

### Cenário: rejeitar código expirado ou reutilizado
- **Dado** que o código expirou ou já foi consumido
- **Quando** o dispositivo tenta confirmar o pareamento
- **Então** o Xano rejeita a operação sem vincular o dispositivo

## RF-IOT-03: Eventos confiáveis
Eventos exigem assinatura válida, timestamp e chave idempotente. Evento inválido ou repetido não altera estado.

### Cenário: aceitar um evento assinado uma única vez
- **Dado** que a chave pública do dispositivo está vinculada à conta
- **E** que o evento possui assinatura e timestamp válidos
- **Quando** o evento é recebido pela primeira vez
- **Então** o Xano armazena a leitura e atualiza o último contato

### Cenário: rejeitar assinatura inválida ou repetição
- **Dado** que a assinatura é inválida ou a chave idempotente já foi usada para o dispositivo
- **Quando** o evento é recebido
- **Então** o Xano recusa a gravação e mantém o estado anterior

## RF-IOT-04: Estado sem hardware
Sem dispositivo conectado, a interface informa a ausência e oferece início do pareamento; não exibe telemetria inventada.

### Cenário: conta sem dispositivo
- **Dado** que a lista autenticada de dispositivos está vazia
- **Quando** a pessoa abre a página de dispositivos
- **Então** a página informa que nenhum dispositivo está conectado e oferece o fluxo de pareamento
- **E** não exibe eventos nem leituras fictícias

## RF-IOT-05: Estado de conexão
A interface distingue pareamento pendente, conexão ativa e dispositivo sem contato com base no estado devolvido pelo servidor.

### Cenário: apresentar estados reais do dispositivo
- **Dado** que o Xano informa `pareamento_pendente`, `conectado` ou `sem_contato`
- **Quando** a lista ou detalhe do dispositivo é exibido
- **Então** a interface apresenta o rótulo correspondente e não infere estado a partir de dados ausentes