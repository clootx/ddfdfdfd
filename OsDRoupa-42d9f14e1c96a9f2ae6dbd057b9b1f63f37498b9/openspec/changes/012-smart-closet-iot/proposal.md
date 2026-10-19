# Proposta — 012-smart-closet-iot

## Contexto

O armário digital organiza roupas, mas ainda não possui conexão com sensores ou dispositivos. A integração deve começar por páginas de dispositivos e um pareamento seguro, sem exibir telemetria fictícia.

## Objetivo

Preparar a experiência do armário inteligente para parear dispositivos autorizados e consultar seu estado real quando hardware e APIs estiverem disponíveis.

## Escopo incluído

- `/dispositivos`: lista privada e estado de conexão.
- `/dispositivos/conectar`: fluxo para inserir ou ler código de pareamento.
- `/dispositivo?id={id}`: detalhe e eventos recebidos.
- Definir contratos Xano para pareamento de uso único, dispositivos do cliente e eventos autenticados.
- Mostrar estado vazio/indisponível sem criar leituras ou confirmações falsas.

## Fora do escopo

- Fabricar, provisionar ou conectar hardware físico nesta change.
- Exibir telemetria gerada localmente como dado real.
- Controlar fechaduras, energia ou outros atuadores.

## Dependências

Hardware precisa publicar identificador e protocolo de pareamento. Xano precisa armazenar dispositivo, vínculo com cliente, credenciais rotativas e eventos autenticados antes de liberar o fluxo.
