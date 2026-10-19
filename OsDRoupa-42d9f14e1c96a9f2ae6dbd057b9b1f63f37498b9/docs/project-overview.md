# Visão Geral do Projeto — OSDroupa

## 1. Informações Básicas e Histórico
- **Projeto:** OSDroupa — Plataforma Integrada de Gestão de Roupas, E-commerce e Arara Inteligente Conectada
- **Data de Início do Projeto:** 14/09/2026 (14/9)
- **Responsável/Contato:** Bruno Magno (Impacta)
- **Metodologia de Evolução:** OpenSpec (Schema `spec-driven`) com fatias verticais incrementais

---

## 2. Contexto do Sistema

O **OSDroupa** é uma solução que une e-commerce têxtil, confecção sob demanda e experiência de guarda-roupa inteligente com IoT e Inteligência Artificial. O projeto conecta um backend robusto em Xano (com banco relacional PostgreSQL, endpoints XanoScript e integrações externas) a uma interface reativa e moderna em Python utilizando Reflex.

O projeto teve seu desenvolvimento iniciado em **14/09/2026**, com a estruturação das tabelas de domínio, autenticação de usuários, modelagem de processos industriais/logísticos (OP/OE) e fluxos financeiros.

---

## 3. Stack Tecnológica Atual

### Frontend
- **Reflex (Python):** Interface reativa orientada a estados (`rx.State`), componentes visuais, animações SVG (arara de roupas swing, tags de temperatura/ocasião), suporte a modo claro/escuro.
- **Ambiente:** `venv` nativo do Python + `pip` gerenciado via `requirements.txt`.
- **Agent Skills:** `reflex-docs`, `setup-python-env`, `reflex-process-management`.

### Backend
- **Xano & XanoScript:** APIs REST, regras de negócio e controle de acesso.
- **Banco de Dados:** PostgreSQL relacional gerenciado no Xano.
- **Grupos de API:** `authentication`, `PANELA_DE_BARRO`, `members_accounts`, `db_bruno_magno`, `event_logs`, `sendgrid_validation`.

### Integrações Externas Ativas no Backend
- **Asaas Sandbox:** Criação de clientes (`/v3/customers`), emissão de cobranças (`criarcobranca`) e tokenização de cartões de crédito.
- **SendGrid:** Envio de e-mails transacionais básicos e dinâmicos (`sendgrid_basic_send`, `sendgrid_dynamic_send`).
- **Agentes e IA no Xano:** Agente conversacional e tools integradas (`xano_example_agent`, `search_xano_docs`).

### IoT e Extensões Físicas
- **RFID:** Rastreamento unitário de peças na arara e no estoque.
- **LEDs Pick-to-Light:** Indicação visual de localização das peças para separação ou composição de look.
- **Contexto Climático/Ocasião:** Recomendações dinâmicas de looks com base na temperatura e no evento (ex.: 22°C — Reunião).

---

## 4. Mapeamento Completo de Funções Existentes vs. OpenSpec

A auditoria do repositório revelou um ecossistema amplo já modelado no backend que agora está sendo progressivamente cadastrado e especificado no OpenSpec:

| Módulo / Capacidade | Artefatos no Código (Xano / Reflex) | Status no OpenSpec |
|---|---|---|
| **1. Identidade e Cliente** | Tabelas `user`, `account`, `CLIENTE`, `STATUS_CLIENTE`; APIs `/auth/login`, `/auth/signup`, `/auth/me`, `cadastra_cliente`; Reflex `AuthState` | **Change 001 Concluída & Arquivada** |
| **2. Endereço e CEP** | Tabelas `endereco`, `cep`, `tipoendereco`; APIs `busca_cep`, `upsert_cep`, `salva_endereco`, `atualiza_endereco`, `marcar_endereco_padrao`, `consulta_endereco_do_cliente` | **Change 002 (Ativa / Em Planejamento)** |
| **3. Catálogo de Roupas** | Tabelas `produto` (Nome, Descricao, Qtd_Disp, Url_Imagem, Preco, Precisa_Produzir) | Pendente de Change (Change 003) |
| **4. Pedidos e Itens** | Tabelas `pedido`, `item`, `status_pedido`, `status_item` (Nfc_E, Cod_Entrega, Total) | Pendente de Change (Change 004) |
| **5. Operações & Produção** | Tabelas `op` (Ordem de Produção), `oe` (Ordem de Execução/Entrega), `status_op`, `status_oe` | Pendente de Change (Change 005) |
| **6. Pagamentos Asaas** | APIs `criarclienteassas`, `criarcobranca`, `toknzcartao`; Tabelas `cartaotoknzd`, `transacao`, `status_transacao`, `ttokenizacao` | Pendente de Change (Change 006) |
| **7. Cancelamento e Estorno** | Tabelas `solcancelamento`, `status_solcancelamento`, `testorno`, `status_testorno` | Pendente de Change (Change 007) |
| **8. Comunicação / E-mail** | Funções Xano `sendgrid_basic_send`, `sendgrid_dynamic_send` | Pendente de Change (Change 008) |
| **9. Suporte e Auditoria** | Tabelas `faq`, `event_log` | Pendente de Change (Change 009) |
| **10. IA & Recomendação** | Agente `xano_example_agent`, `agent_conversation`, `agent_message`, lógica de recomendação por clima | Pendente de Change (Change 010) |
| **11. Hardware IoT Arara** | Tags RFID e LEDs Pick-to-Light integrados à interface de arara inteligente | Pendente de Change (Change 011) |

---

## 5. Princípios de Desenvolvimento e Evolução

1. **Evolução por Fatias Verticais:** Cada funcionalidade só é integrada ao frontend após contrato claro no OpenSpec e endpoints validados no Xano.
2. **Segurança no Backend:** O backend é a fonte de integridade; o frontend Reflex nunca substitui validações de autorização.
3. **Respeito ao Domínio:** A estrutura do negócio é preservada sem alterações desnecessárias de schema.
