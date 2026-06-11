# POC RAG — Manutenção Preditiva Industrial

Assistente de IA com RAG (Retrieval-Augmented Generation) para consultas sobre manutenção preditiva e OEE, baseado no dataset público AI4I 2020.

## Stack

- **Backend:** Python · FastAPI
- **RAG:** LangChain · ChromaDB · sentence-transformers (`all-MiniLM-L6-v2`)
- **LLM:** Groq API (`llama-3.3-70b-versatile`)
- **Frontend:** HTML/CSS/JS (servido pelo FastAPI)
- **Automação:** n8n
- **Infraestrutura:** Docker

## Estrutura do Projeto

```
poc-rag/
├── backend/
│   ├── main.py           # API FastAPI
│   ├── rag.py            # Pipeline RAG (busca + geração)
│   ├── ingest.py         # Indexação do dataset no ChromaDB
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html        # Interface de chat
├── data/
│   └── ai4i2020.csv      # Dataset (não versionado)
├── chroma_db/            # Banco vetorial (não versionado)
├── docker-compose.yml
├── .env                  # Variáveis de ambiente (não versionado)
└── .env.example
```

## Como Rodar

### 1. Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado
- Chave de API do Groq: [console.groq.com](https://console.groq.com)

### 2. Clone o repositório

```bash
git clone https://github.com/SEU_USUARIO/poc-rag.git
cd poc-rag
```

### 3. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` e preencha:

```env
GROQ_API_KEY=sua_chave_aqui
CHROMA_PATH=/app/chroma_db
```

### 4. Baixe o dataset

Acesse [Kaggle — AI4I 2020 Predictive Maintenance](https://www.kaggle.com/datasets/stephanmatzka/predictive-maintenance-dataset-ai4i-2020) e salve o arquivo como:

```
data/ai4i2020.csv
```

### 5. Suba os containers

```bash
docker compose up --build
```

O container `ingest` indexa os dados automaticamente na primeira execução (~2 minutos).

### 6. Acesse

| Serviço | URL |
|---------|-----|
| Chat (frontend) | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| n8n (automações) | http://localhost:5678 |

## Endpoints da API

### `GET /health`
Verifica se o backend está no ar.

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### `POST /query`
Faz uma consulta RAG.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Qual é o OEE médio das máquinas?"}'
```

Resposta:
```json
{
  "resposta": "...",
  "documentos_usados": ["..."]
}
```

### `POST /ingest`
Re-indexa o dataset (pode ser chamado pelo n8n via webhook).

```bash
curl -X POST http://localhost:8000/ingest
```

## Exemplos de Perguntas

**OEE**
- `Qual é o OEE médio das máquinas?`
- `O que é OEE e como é calculado?`
- `Quais são os benchmarks de OEE classe mundial?`

**Falhas**
- `Quais são os tipos de falha mais comuns?`
- `O que causa falha por desgaste de ferramenta (TWF)?`
- `Qual faixa de torque está associada a mais falhas?`

**Diagnóstico**
- `Minha máquina tem OEE de 55%, o que verificar primeiro?`
- `Como priorizar ações para reduzir paradas?`

## Dataset

**AI4I 2020 Predictive Maintenance Dataset** — 10.000 registros com:

| Campo | Descrição |
|-------|-----------|
| `Air temperature [K]` | Temperatura do ar |
| `Process temperature [K]` | Temperatura do processo |
| `Rotational speed [rpm]` | Velocidade rotacional |
| `Torque [Nm]` | Torque |
| `Tool wear [min]` | Desgaste da ferramenta |
| `Machine failure` | Indicador de falha (0/1) |
| `TWF`, `HDF`, `PWF`, `OSF`, `RNF` | Tipos de falha |

## Arquitetura

```
[Dataset CSV]
     ↓
[ingest.py] → embeddings (all-MiniLM-L6-v2) → [ChromaDB]
                                                     ↓
[Frontend HTML] → POST /query → [LangChain RAG] → [Groq LLM]
                                                     ↓
[n8n Workflows] → webhooks → /query ou /ingest    Resposta
```

## n8n Workflows

| Workflow | Gatilho | Função |
|----------|---------|--------|
| Chat RAG | Webhook POST `/rag-query` | Expõe o RAG para sistemas externos |
| Chat UI Nativo | Chat Trigger | Interface de chat no próprio n8n |
| Re-indexação | Schedule (domingo 2h) | Reindexação automática |
| Alerta OEE | Webhook POST `/oee-alerta` | Calcula OEE e gera diagnóstico se < 40% |

## Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `GROQ_API_KEY` | Chave da API do Groq (obrigatória) |
| `CHROMA_PATH` | Caminho do banco vetorial (padrão: `/app/chroma_db`) |
