# OSDroupa — Plataforma de Guarda-Roupa Inteligente & E-commerce

> **Início do Projeto:** 14/09/2026 (14/9)  
> **Arquitetura:** Frontend em Python com [Reflex](https://reflex.dev) + Backend em [Xano](https://www.xano.com) (PostgreSQL) + Gestão por [OpenSpec](https://openspec.dev)

---

## 🚀 Como Executar o Projeto Localmente

Com o ambiente virtual ativado no terminal:

```powershell
# Ativar o ambiente virtual (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Executar a aplicação Reflex em modo de desenvolvimento
reflex run
```

A aplicação estará disponível em:
- 🌐 **Página Inicial (Entrar / Login):** [http://localhost:3000/](http://localhost:3000/)
- 🌐 **Página de Cadastro (Criar Conta):** [http://localhost:3000/cadastro](http://localhost:3000/cadastro)
- ⚙️ **Backend FastAPI / Reflex Engine:** [http://localhost:8000](http://localhost:8000)

---

## 🧭 Mapa de Navegação do Repositório: Onde Encontrar Tudo

### 1. 🔄 OpenSpec e Gestão de Mudanças (Changes)
Todas as evoluções do sistema são planejadas e executadas através do OpenSpec:
- 📁 **Changes Ativas e Planejadas:** [`openspec/changes/`](openspec/changes/)
  - 🚀 **Change 002 (Ativa):** [`openspec/changes/002-auth-landing-page/`](openspec/changes/002-auth-landing-page/) — Refatoração da Página Inicial (Login, Cadastro, Medidor de Força e Arara Animada).
  - 📋 **Change 003 (Planejada):** [`openspec/changes/003-address-and-cep/`](openspec/changes/003-address-and-cep/) — Gestão de Endereços, Consulta e Upsert de CEP e Vínculo ao Cliente.
- 📦 **Histórico de Changes Concluídas:** [`openspec/changes/archive/`](openspec/changes/archive/)
  - `001-foundation-identity-client`: Fundação de identidade e clientes.
- 📜 **Especificações Consolidadas (Fonte da Verdade):** [`openspec/specs/`](openspec/specs/)
  - [`auth/spec.md`](openspec/specs/auth/spec.md): Requisitos canônicos de autenticação e sessão.
  - [`cliente/spec.md`](openspec/specs/cliente/spec.md): Requisitos canônicos do perfil de cliente.
- 🛠️ **Templates para Novas Changes:** [`openspec/templates/`](openspec/templates/)
- ⚙️ **Configuração dos Workflows:** [`openspec/config.yaml`](openspec/config.yaml)

---

### 2. 📐 Páginas de Modelagem e Arquitetura do Projeto
Toda a documentação conceitual e técnica está centralizada em:
- 📘 **Central de Modelagem (Hub Principal):** [`docs/README.md`](docs/README.md)
- 📐 **Modelo Conceitual de Domínio:** [`docs/domain-model.md`](docs/domain-model.md) — Entidades, atributos e regras conceituais (User, Cliente, Pedido, Produto, Endereço, etc.).
- 🌐 **Visão Geral e Contexto Técnico:** [`docs/project-overview.md`](docs/project-overview.md) — Problema, objetivos, público, stack, Asaas, SendGrid e IoT.

---

### 3. 🗄️ Backend e Banco de Dados (Xano)
- 📊 **Modelos Físicos de Dados (32 tabelas PostgreSQL):** [`xano/table/`](xano/table/)
- 🔌 **Endpoints e Regras de Negócio (APIs REST):** [`xano/api/`](xano/api/)
  - `panela_de_barro`: Endereços, CEPs, clientes, integração Asaas e tokenização de cartões.
  - `authentication`: Cadastro, login e sessão do usuário.
  - `db_bruno_magno`: Operações de dados de pedidos, itens e produtos.
- 🤖 **Agente de IA e Ferramentas:** [`xano/ai/`](xano/ai/)

---

### 4. 💻 Frontend Reativo (Reflex em Python)
- 🖥️ **Código da Aplicação Principal:** [`OSDroupa/OSDroupa.py`](OSDroupa/OSDroupa.py) — Páginas, estados (`AuthState`), animação SVG da arara e formulários.
- ⚙️ **Configuração da Aplicação e Temas:** [`rxconfig.py`](rxconfig.py)
- 📦 **Dependências Python:** [`requirements.txt`](requirements.txt)

---

### 5. 📚 Diretrizes do Projeto e Material do Professor
- 🤖 **Instruções para Agentes de IA:** [`AGENTS.md`](AGENTS.md) — Regras de código, Reflex Agent Skills e ciclo OpenSpec.
- 🎓 **Material de Referência Acadêmica:** [`professormateria/`](professormateria/)
  - [`Preparação de um Projeto com OpenSpec.md`](professormateria/Preparação%20de%20um%20Projeto%20com%20OpenSpec.md)
  - [`1. Explore inicial.txt`](professormateria/1.%20Explore%20inicial.txt)
  - [`apendice_B_reflex.md`](professormateria/apendice_B_reflex.md)
