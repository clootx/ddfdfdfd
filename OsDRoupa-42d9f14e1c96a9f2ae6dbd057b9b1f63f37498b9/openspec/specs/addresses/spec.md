# Especificação consolidada — Gestão de Endereços e CEP

## RF-END-01: Consulta e preenchimento de CEP
CEP é validado como oito dígitos; a resposta válida preenche os campos públicos do endereço.

## RF-END-02: Múltiplos endereços
Cada cliente pode manter vários endereços. O schema não pode impor unicidade de `cliente_id` e `tipoendereco_id`.

## RF-END-03: Propriedade e autorização
Os endpoints de leitura e mutação exigem `auth=user`, resolvem `CLIENTE` por `$auth.id` e verificam propriedade do endereço. `cliente_id` enviado pelo navegador nunca autoriza uma operação.

## RF-END-04: Endereço padrão
Ao marcar endereço padrão, o Xano verifica propriedade e desmarca os demais endereços do mesmo cliente.

## RF-END-05: Transporte de token
O JWT é enviado em `Authorization: Bearer <token>` e não aparece em URL ou query string.

## Cenário: operação em endereço de outra conta
- **Dado** que um endereço pertence a outro cliente
- **Quando** a conta autenticada tenta alterá-lo ou marcá-lo como padrão
- **Então** a operação é negada sem modificar qualquer dado

## Cenário: endereço adicional
- **Dado** que um cliente já tem endereço cadastrado
- **Quando** salva um novo endereço
- **Então** ambos permanecem associados ao cliente e a escolha de padrão é exclusiva