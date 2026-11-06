# OSDroupa — Plataforma de Guarda-Roupa Inteligente & E-commerce

## Backend para apresentação (Xano)

Para apresentar e entregar o trabalho utilizando Xano, execute a aplicação com `OSDROUPA_BACKEND=xano`. O Xano deve ser a fonte de verdade dos dados compartilhados e validar as operações protegidas. Os arquivos `.xs` em `xano/` descrevem tabelas e endpoints, mas mudanças feitas no repositório precisam ser aplicadas ao workspace Xano antes da apresentação. O exemplo de ambiente está em `.env.example`.

```powershell
# Executar usando o Xano (modo da apresentação)
$env:OSDROUPA_BACKEND = "xano"
reflex run
```

## Backend local de apoio (SQLite)

SQLite permanece disponível para desenvolvimento offline em uma máquina. No primeiro acesso, o app cria `data/osdroupa.sqlite3`; esses dados não sincronizam entre dispositivos. Para escolher esse modo explicitamente:

```powershell
$env:OSDROUPA_BACKEND = "sqlite"
$env:OSDROUPA_DB_PATH = "C:\caminho\osdroupa.sqlite3"
reflex run

# O comando set-admin abaixo altera somente a base SQLite local.
..\.venv\Scripts\python.exe -m OSDroupa.local_backend set-admin voce@exemplo.com
```

Pedidos demonstrativos reservam o estoque por até 24 horas e não cobram. Para produtos marcados como venda real, o backend SQLite pode abrir um checkout do Mercado Pago quando `MERCADOPAGO_ACCESS_TOKEN` estiver configurado; a confirmação depende do webhook assinado. Veja [pagamentos e pendências de lançamento](docs/payment-and-launch-checklist.md). As variáveis de integração estão listadas em `.env.example`. Com SMTP configurado (`OSDROUPA_SMTP_HOST`, `OSDROUPA_SMTP_FROM`, `OSDROUPA_SMTP_USER`, `OSDROUPA_SMTP_PASSWORD` e, opcionalmente, `OSDROUPA_SMTP_PORT`/`OSDROUPA_PUBLIC_URL`), a recuperação envia e-mail. Sem SMTP, o modo local oferece um link de redefinição na própria tela; nenhum e-mail é enviado. Desative esse recurso com `OSDROUPA_LOCAL_RECOVERY=0` quando necessário. O pareamento local também é uma demonstração e não conecta sensores físicos. SQLite é para desenvolvimento e uma única instância; produção compartilhada requer um banco servidor.

> **Início do Projeto:** 14/09/2026 (14/9)  
> **Arquitetura:** Frontend Reflex; Xano como backend da apresentação e SQLite opcional para desenvolvimento local; mudanças acompanhadas por OpenSpec.

---

## 🚀 Como Executar o Projeto no Seu PC (Windows)

Cada pessoa roda a própria cópia: os dados ficam só no PC dela (SQLite) e cada uma usa a própria chave do Gemini.

**Pré-requisitos:** Python **3.12** ([python.org](https://www.python.org/downloads/), marque "Add Python to PATH") e [Git](https://git-scm.com/).

**1. Baixar o projeto** (PowerShell):

```powershell
cd $HOME\Downloads
git clone https://github.com/clootx/ddfdfdfd.git osdroupa
cd osdroupa\OsDRoupa-42d9f14e1c96a9f2ae6dbd057b9b1f63f37498b9
```

O projeto fica na pasta interna (a de nome comprido); rode todos os comandos a partir dela.

**2. Criar o ambiente e instalar:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1     # se for bloqueado: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```

**3. Configurar:**

```powershell
copy .env.example .env
notepad .env
```

O `.env.example` já vem pronto para rodar localmente (`OSDROUPA_BACKEND=sqlite`, `GEMINI_MODEL=gemini-3.6-flash`). Só preencha `GEMINI_API_KEY` com a sua chave gratuita de [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Sem chave, o app funciona e o Look do Dia usa a sugestão básica. O `.env` é pessoal: não envie para ninguém nem para o Git.

**4. Rodar:**

```powershell
reflex run
```

A primeira execução demora alguns minutos (baixa as dependências do site). Quando aparecer `App running at: http://localhost:3000`, abra o endereço e crie sua conta. O banco `data/osdroupa.sqlite3` é criado automaticamente.

**Problemas comuns:**
- Porta ocupada: `reflex run --frontend-port 3001 --backend-port 8001`.
- Tela recarregando sozinha a cada poucos segundos: pare (Ctrl+C) e rode `reflex run --env prod`.
- Conta administradora (telas de gestão): antes de cadastrar, adicione `OSDROUPA_ADMIN_EMAIL=seu@email.com` ao `.env`.

A aplicação estará disponível em:
- 🌐 **Página Inicial (Entrar / Login):** [http://localhost:3000/](http://localhost:3000/)
- 🌐 **Página de Cadastro (Criar Conta):** [http://localhost:3000/cadastro](http://localhost:3000/cadastro)
- ⚙️ **Backend FastAPI / Reflex Engine:** [http://localhost:8000](http://localhost:8000)

### Configuração (`.env`)

Copie `.env.example` para `.env` **na raiz do projeto** (mesma pasta do `rxconfig.py`). O app carrega esse arquivo ao iniciar; variáveis definidas no terminal têm prioridade. O `.env` é ignorado pelo Git — nunca o versione. Sem `OSDROUPA_BACKEND`, o código usa SQLite.

### Estilista com IA (Google Gemini, plano gratuito)

- Defina `GEMINI_API_KEY` (gerada em aistudio.google.com) e, se quiser, `GEMINI_MODEL` (o `.env.example` usa `gemini-3.6-flash`; sem a variável, o código usa `gemini-3.8-flash`). A chave é lida só no servidor Reflex.
- Sem a chave, o Look do Dia usa a sugestão básica por regras.
- Limites persistentes no SQLite local (por conta/hora, por minuto e por dia, com pausa após erro 429) em `OSDROUPA_AI_*`; ajuste conforme a cota mostrada em aistudio.google.com/rate-limit.
- Geração de imagens é **paga** e fica desligada (`OSDROUPA_IMAGES_ENABLED=false`).
- Personalização (perfil de estilo e avaliações 👍/👎) pode ser desligada por cada pessoa no perfil. No plano gratuito, o Google pode usar o conteúdo enviado para melhorar os produtos dele; por isso só dados mínimos são enviados (veja a Política de Privacidade no app e as Changes 029 e 030).

### Testes

```powershell
pip install -r requirements-dev.txt
pytest                 # usa bancos SQLite temporários e provedores falsos (MOCK); não toca em data/
pyflakes OSDroupa professormateria tests rxconfig.py
pytest -m live         # chamadas REAIS (Open-Meteo e uma ao Gemini); só com autorização e plano gratuito
```

---

## 🧭 Mapa de Navegação do Repositório: Onde Encontrar Tudo

### 1. OpenSpec e gestão de mudanças
Todas as evoluções funcionais são acompanhadas por changes e especificações:
- **Changes e progresso:** [`openspec/changes/README.md`](openspec/changes/README.md)
- **Change 002:** checklist concluído; login, cadastro e página institucional.
- **Change 004:** checklist concluído; autenticação com Xano.
- **Única change ativa:** [`023-consolidacao-geral-do-projeto`](openspec/changes/023-consolidacao-geral-do-projeto/); reúne as specs, decisões e pendências dos módulos anteriores.
- **Histórico:** [`openspec/changes/archive/README.md`](openspec/changes/archive/README.md); as pastas de origem foram arquivadas sem apagar seus checklists.
- **Especificações consolidadas:** [`openspec/specs/`](openspec/specs/)
- **Templates e configuração:** [`openspec/templates/`](openspec/templates/) e [`openspec/config.yaml`](openspec/config.yaml)

### 2. 📐 Páginas de Modelagem e Arquitetura do Projeto
Toda a documentação conceitual e técnica está centralizada em:
- 📘 **Central de Modelagem (Hub Principal):** [`docs/README.md`](docs/README.md)
- 📐 **Modelo Conceitual de Domínio:** [`docs/domain-model.md`](docs/domain-model.md) — Entidades, atributos e regras conceituais (User, Cliente, Pedido, Produto, Endereço etc.).
- 🌐 **Visão Geral e Contexto Técnico:** [`docs/project-overview.md`](docs/project-overview.md) — Stack, funcionalidades locais, integrações e pendências.
- 🗂️ **Estrutura de pastas:** [`docs/project-structure.md`](docs/project-structure.md) — Mapa do repositório e caminhos de runtime que devem permanecer no lugar.
- 💳 **Pagamentos e lançamento:** [`docs/payment-and-launch-checklist.md`](docs/payment-and-launch-checklist.md) — Mercado Pago, configuração e o que falta para produção.

### 3. 🗄️ Backend e Banco de Dados (Xano e SQLite local)
- A apresentação deve usar Xano (`OSDROUPA_BACKEND=xano`). SQLite é uma alternativa local explícita; configure `OSDROUPA_DB_PATH` para escolher onde guardar esse arquivo.
- 📊 **Modelos Físicos de Dados (39 arquivos de tabela Xano):** [`xano/table/`](xano/table/)
- 🔌 **Endpoints e Regras de Negócio (APIs REST):** [`xano/api/`](xano/api/)
  - `panela_de_barro`: Endereços, CEPs e clientes; os rascunhos locais Asaas estão bloqueados. O workspace Xano remoto não foi alterado.
  - `authentication`: Cadastro, login e sessão do usuário.
  - `db_bruno_magno`: Operações de dados de pedidos, itens e produtos.
- 🤖 **Agente de IA e Ferramentas:** [`xano/ai/`](xano/ai/)

### 4. 💻 Frontend Reativo (Reflex em Python)
- 🖥️ **Código da Aplicação Principal:** [`OSDroupa/OSDroupa.py`](OSDroupa/OSDroupa.py) — Páginas, estados (`AuthState`), animação SVG da arara e formulários.
- ⚙️ **Configuração da Aplicação e Temas:** [`rxconfig.py`](rxconfig.py)
- 📦 **Dependências Python:** [`requirements.txt`](requirements.txt)

### 5. 📚 Diretrizes do Projeto e Material do Professor
- 🤖 **Instruções para Agentes de IA:** [`AGENTS.md`](AGENTS.md) — Regras de código, Reflex Agent Skills e ciclo OpenSpec.
- 🎓 **Material de Referência Acadêmica:** [`professormateria/`](professormateria/)
  - [`Preparação de um Projeto com OpenSpec.md`](professormateria/Preparação%20de%20um%20Projeto%20com%20OpenSpec.md)
  - [`1. Explore inicial.txt`](professormateria/1.%20Explore%20inicial.txt)
  - [`apendice_B_reflex.md`](professormateria/apendice_B_reflex.md)
