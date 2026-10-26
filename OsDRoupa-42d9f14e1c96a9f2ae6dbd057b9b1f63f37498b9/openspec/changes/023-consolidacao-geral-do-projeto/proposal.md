# Proposta — 023-consolidacao-geral-do-projeto

## Contexto

O repositório acumulou changes OpenSpec ativas e concluídas que descrevem partes relacionadas do mesmo produto. Isso espalha requisitos, decisões e pendências entre 19 pastas e deixa incerto qual lista deve orientar a próxima entrega. Há ainda diferenças de prioridade entre os artefatos: Xano é requisito da entrega, enquanto SQLite existe como backend local; o fluxo de pagamento ativo usa Mercado Pago, embora changes antigas ainda citem Asaas.

## Objetivo

Manter uma única change ativa como plano rastreável do OSDroupa, reunindo especificações, decisões técnicas e checklists das changes anteriores. Organizar a documentação do projeto e a saída de logs sem alterar caminhos necessários à execução do Reflex, do Xano ou das ferramentas de desenvolvimento.

## Escopo

- Consolidar propostas, designs, specs e tarefas das 19 pastas existentes em `openspec/changes/` numa change modular.
- Preservar o estado de cada tarefa: itens verificados continuam marcados; validações pendentes permanecem abertas.
- Arquivar as pastas de origem como histórico e registrar que suas pendências foram transferidas para esta change.
- Declarar Xano como backend da entrega; manter SQLite como opção de desenvolvimento local e fallback.
- Alinhar prioridades de domínio: Mercado Pago substitui os rascunhos antigos de Asaas; imagens demonstrativas locais permanecem válidas sem credenciais de geração; integrações de e-mail e IoT dependem de configuração externa/hardware.
- Documentar a estrutura de pastas e mover logs de execução do diretório raiz para `logs/` sem apagar seu conteúdo.

## Fora de escopo

- Reescrever páginas, serviços, APIs ou regras de negócio apenas para consolidar documentação.
- Mover `OSDroupa/`, `assets/`, `xano/`, `.web/`, `.states/`, `.venv/`, `data/`, `uploaded_files/` ou `reflex.lock/`; Reflex e Xano dependem desses caminhos.
- Declarar recursos concluídos sem validação, publicar alterações no workspace Xano ou habilitar pagamento real.

## Critério de conclusão

Existe uma única pasta ativa em `openspec/changes/`; ela contém o plano e requisitos de todas as origens, mantém as pendências abertas, e o índice/documentação explicam a organização atual. O projeto continua usando seus caminhos de runtime existentes.