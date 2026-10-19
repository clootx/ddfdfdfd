# Índice de Changes — OpenSpec (OSDroupa)

Este diretório reúne as propostas e fatias verticais de evolução do projeto **OSDroupa**, organizadas estritamente sob o schema `spec-driven`.

---

## 🧭 Onde encontrar as Changes:

| Status | Identificador | Título / Descrição | Onde encontrar |
|---|---|---|---|
| 📦 **Arquivada** | `001-foundation-identity-client` | Fundação de Identidade, Autenticação e Perfil de Cliente | [`archive/001-foundation-identity-client/`](./archive/001-foundation-identity-client/) |
| 🚀 **Ativa** | `002-auth-landing-page` | Refatoração da Página Inicial (Entrar, Cadastro, Medidor de Força e Arara) | [`002-auth-landing-page/`](./002-auth-landing-page/) |
| 🚀 **Ativa** | `003-address-and-cep` | Gestão de Endereços, Consulta e Upsert de CEP e Vinculação ao Cliente | [`003-address-and-cep/`](./003-address-and-cep/) |
| ✅ **Concluída** | `004-auth-integration-xano` | Integração de Autenticação com Xano (Login Real, Cadastro, JWT e Dashboard) | [`004-auth-integration-xano/`](./004-auth-integration-xano/) |
| 🚀 **Ativa** | `005-dashboard-retirement` | Remoção da página Dashboard e destino pós-autenticação em “Como funciona” | [`005-dashboard-retirement/`](./005-dashboard-retirement/) |
| 🚀 **Ativa** | `006-persistent-account-profile-wardrobe` | Sessão Persistente, Perfil e Armário Pessoal | [`006-persistent-account-profile-wardrobe/`](./006-persistent-account-profile-wardrobe/) |
| 🚀 **Ativa** | `007-storefront-catalog` | Loja, catálogo Xano, detalhe de produto e sacola persistente | [`007-storefront-catalog/`](./007-storefront-catalog/) |
| 🚀 **Ativa** | `008-orders-checkout-payments` | Checkout PIX autenticado, pedidos e cobranças Asaas | [`008-orders-checkout-payments/`](./008-orders-checkout-payments/) |
| 🚀 **Ativa** | `009-wardrobe-cloud-sync` | Armário do cliente sincronizado com Xano e migração local idempotente | [`009-wardrobe-cloud-sync/`](./009-wardrobe-cloud-sync/) |
| 🚀 **Ativa** | `010-management-console` | Console administrativa para catálogo, pedidos, clientes e relatórios | [`010-management-console/`](./010-management-console/) |
| 🚀 **Ativa** | `011-content-inspiration-challenges` | Inspiração, artigos editoriais e desafios pessoais | [`011-content-inspiration-challenges/`](./011-content-inspiration-challenges/) |
| 🚀 **Ativa** | `012-smart-closet-iot` | Dispositivos e pareamento seguro para o armário inteligente | [`012-smart-closet-iot/`](./012-smart-closet-iot/) |

---

## 📁 Estrutura Padrão de cada Change:

Cada pasta de change contém obrigatoriamente os 4 artefatos definidos pelo OpenSpec:

```text
nome-da-change/
├── proposal.md       # Contexto, objetivos, escopo incluído e excluído
├── specs/            # Requisitos funcionais (RF-xx) e cenários BDD (Dado/Quando/Então)
│   └── modulo.md
├── design.md         # Arquitetura técnica (Reflex + Xano), contratos de API e modelos
└── tasks.md          # Checklist sequencial de tarefas para o workflow Apply
```

---

## 🛠️ Como criar uma nova Change:
Utilize os modelos pré-configurados em:
👉 [`../templates/`](../templates/)
