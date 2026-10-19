# Proposta — 009-wardrobe-cloud-sync

## Contexto

A Change 006 guarda o armário no `localStorage`, separado por ID do usuário. Isso protege contra mistura casual entre contas no mesmo navegador, mas não sincroniza dados entre dispositivos e perde alterações quando o armazenamento local é apagado. O Xano ainda não possui entidade para roupas pessoais.

## Objetivo

Fazer do Xano a fonte de verdade do armário por cliente, preservando os itens locais existentes durante a migração e mantendo a interface utilizável enquanto as novas APIs não forem publicadas.

## Escopo incluído

- Criar tabela privada para peças do cliente, com proprietário, categoria e chave local idempotente.
- Criar leitura, inclusão e remoção autenticadas; o cliente é derivado do token.
- Sincronizar o armário de `/armario` com Xano e migrar itens existentes sem duplicá-los.
- Manter cache local por conta e indicar claramente quando a página estiver sem sincronização.

## Fora do escopo

- Upload de fotos, recomendações de looks, compartilhamento e análise por IA.
- Usar `PRODUTO` como armário pessoal.
- Publicar alterações no workspace Xano ou migrar dados sem revisão.

## Riscos e dependências

- Fontes Xano são locais e precisam ser importadas/testadas antes da sincronização entre dispositivos funcionar.
- A migração envia itens existentes ao Xano na primeira leitura bem-sucedida. A chave `chave_local` e seu índice único evitam duplicações em recargas e repetição de rede.
