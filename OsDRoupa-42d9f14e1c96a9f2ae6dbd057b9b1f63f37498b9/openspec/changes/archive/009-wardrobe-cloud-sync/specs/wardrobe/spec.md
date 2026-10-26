# Especificação — Armário sincronizado

## RF-WARD-01: Privacidade

O backend deve associar cada peça ao cliente autenticado e retornar somente dados desse cliente.

### Cenário: leitura de armário próprio
- **Dado** que a pessoa está autenticada
- **Quando** abre o armário
- **Então** recebe apenas peças vinculadas ao cliente daquela sessão

### Cenário: remoção de item alheio
- **Dado** que o ID pertence a outra conta
- **Quando** uma pessoa tenta removê-lo
- **Então** o Xano recusa a operação sem alterar o registro

## RF-WARD-02: Sincronização e migração

Itens locais existentes devem migrar sem duplicação por meio de `chave_local`; falhas não apagam os dados locais.

## RF-WARD-03: Operações

Pessoa autenticada pode listar, adicionar e remover peças; o servidor valida campos e deriva o proprietário.

## RF-WARD-04: Estado de conexão

Quando o Xano não estiver disponível, o armário mantém o cache local e informa que as alterações podem não estar sincronizadas.
