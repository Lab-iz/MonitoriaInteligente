# Monitoria Inteligente

Plataforma institucional de apoio acadêmico, triagem assistida por IA e atendimento humano de monitoria.

## Visão geral

O sistema organiza dúvidas acadêmicas por disciplina e tema, gera um pré-atendimento assistido por IA, prioriza a fila humana de monitoria e entrega painéis específicos para estudante, monitor, professor e pedagógico/admin.

Princípio central do produto:

- a IA apoia a triagem, a síntese e a recomendação de materiais
- o atendimento humano continua sendo o núcleo pedagógico
- toda saída automática é identificada como sugestão

## Objetivo pedagógico

O MVP foi desenhado para reduzir triagem manual repetitiva, melhorar o contexto das dúvidas, acelerar o primeiro apoio ao estudante e transformar recorrências em inteligência pedagógica institucional.

## Stack utilizada

- Python 3
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Jinja2
- HTML5
- CSS3
- JavaScript puro
- SQLite no desenvolvimento
- Chart.js via CDN para dashboards
- Pytest para testes básicos

## Estrutura do projeto

```text
.
|-- app
|   |-- __init__.py
|   |-- admin
|   |-- auth
|   |-- extensions.py
|   |-- knowledge_base
|   |-- main
|   |-- models
|   |-- monitor
|   |-- reports
|   |-- services
|   |-- shifts
|   |-- static
|   |-- student
|   |-- teacher
|   |-- templates
|   |-- tickets
|   `-- utils
|-- config.py
|-- requirements.txt
|-- run.py
`-- tests
```

## Arquitetura

- `create_app` centraliza configuração, extensões, blueprints e comandos CLI.
- `models/domain.py` concentra o domínio acadêmico do MVP: usuários, vínculos, dúvidas, triagem, conhecimento, plantões, alertas e relatórios.
- `services/` isola as regras de negócio.
  - `triage_service.py`: executa a triagem assistida por IA.
  - `ai_provider.py`: camada desacoplada de IA com provider mock funcional.
  - `assignment_service.py`: prioridade e sugestão de monitor.
  - `risk_alert_service.py`: alertas simples de risco acadêmico.
  - `dashboard_service.py`: agregações dos painéis.
  - `reporting_service.py`: exportação CSV.
  - `ticket_service.py`: abertura, anexos, escalonamento e resposta humana.
- `templates/` entrega uma interface institucional responsiva com dashboards por perfil.

## Funcionalidades implementadas

- autenticação, cadastro e controle de acesso por perfil
- cadastro acadêmico de cursos, turmas, disciplinas, temas, usuários e vínculos
- abertura de dúvidas com contexto, urgência, prazo e anexo opcional
- triagem inicial assistida por IA com classificação, resumo, resposta sugerida e transparência
- escalonamento da dúvida para fila humana
- fila inteligente com prioridade por urgência, prazo, reincidência, risco e adequação do monitor
- painel do estudante com histórico, status, dificuldades e próximos plantões
- painel do monitor com fila priorizada, agenda e histórico de atendimentos
- painel do professor com recorrência por tema, taxa de resolução e validação da base
- painel pedagógico/admin com métricas globais, cobertura e alertas de risco
- base de conhecimento por disciplina com busca, sugestão e validação
- cadastro e visualização de plantões
- avaliação do atendimento e utilidade da resposta da IA
- relatórios básicos com exportação CSV
- trilha de auditoria simples
- seed data realista para demonstração

## Funcionalidades preparadas para expansão

- provider real de IA no lugar do mock, sem reescrever o fluxo web
- novos critérios de priorização da fila
- busca semântica e recomendação mais sofisticada na base de conhecimento
- geração de PDF a partir da camada de relatórios
- histórico ampliado de auditoria e snapshots analíticos
- anexos mais ricos e validação avançada de arquivos
- aprofundamento do papel docente em respostas diretas e aprovação de conteúdo

## Como instalar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Como rodar

```bash
flask --app run.py init-db
flask --app run.py seed-db
flask --app run.py run
```

Ou:

```bash
python run.py
```

## Como popular o banco

```bash
flask --app run.py seed-db
```

## Deploy no Render

O repositorio inclui um `render.yaml` para deploy como Web Service Python.

Configuracao usada pelo Blueprint:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn run:app`
- Health Check Path: `/healthz`
- `FLASK_CONFIG=production`
- `AUTO_INIT_DB=true`
- `SEED_DEMO_DATA=true`
- `SQLITE_DB_PATH=/tmp/monitoria.db`
- `UPLOAD_FOLDER=/tmp/monitoria-uploads`
- `REPORT_FOLDER=/tmp/monitoria-reports`

No primeiro deploy, a aplicacao cria as tabelas automaticamente e popula os dados de demonstracao se o banco estiver vazio.

Se preferir configurar manualmente no painel do Render, use os mesmos comandos acima e crie uma variavel `SECRET_KEY` com valor secreto.

Por padrao, o deploy usa SQLite no `/tmp` do servico para evitar erro de escrita no diretorio do deploy. Sem disco persistente ou banco gerenciado, o Render pode perder esses arquivos em reinicios ou redeploys. Para manter dados reais, use uma destas opcoes:

- Render Postgres: configure `DATABASE_URL` no servico.
- Disco persistente pago: configure `SQLITE_DB_PATH`, `UPLOAD_FOLDER` e `REPORT_FOLDER` apontando para o caminho montado.

## Perfis de teste

O seed cria perfis de todos os papéis institucionais:

- admin/pedagógico
- professor
- monitor
- estudante

Credenciais padrão do ambiente de desenvolvimento:

- admin: usuário `admin` | senha `demo123`
- professor: usuários `helena` e `caio` | senha `demo123`
- monitor: usuários `lia` e `otavio` | senha `demo123`
- estudante: usuários `ana`, `bruno` e `clara` | senha `demo123`

O acesso principal de administração do sistema é `admin` / `demo123`.

## Descrição das telas

- `/auth/login`: acesso institucional
- `/auth/register`: cadastro inicial
- `/student/dashboard`: visão do estudante
- `/monitor/dashboard`: visão do monitor
- `/teacher/dashboard`: visão docente
- `/admin/dashboard`: visão institucional
- `/admin/management`: gestão acadêmica
- `/tickets/new`: abertura de dúvida
- `/tickets/<id>`: detalhe completo da dúvida
- `/tickets/queue`: fila inteligente
- `/knowledge-base/`: base de conhecimento
- `/shifts/`: agenda de plantões
- `/reports/`: relatórios exportáveis

## Camada de IA no MVP

O MVP usa um provider mock desacoplado:

- recebe contexto da dúvida
- procura itens relacionados na base de conhecimento
- gera classificação, resumo, resposta inicial, perguntas de refinamento e confiança
- decide se o caso permanece em triagem ou segue para fila humana

Essa camada está pronta para ser substituída por um provider real mantendo a mesma interface.

## Testes

```bash
pytest
```

Cobertura básica incluída:

- login
- permissão por perfil
- criação de dúvida
- triagem inicial
- encaminhamento para fila humana
- resposta do monitor
- exportação simples de relatório

## Próximos passos recomendados

- integrar LLM real com trilha de prompts versionada
- adicionar edição administrativa e exclusão controlada
- criar filtros mais ricos no dashboard e relatórios por período
- evoluir alertas de risco com múltiplos sinais institucionais
- ampliar testes para serviços e formulários
