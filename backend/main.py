from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from rag import query_rag
from ingest import ingest

app = FastAPI(title="RAG Manutenção Preditiva")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PerguntaRequest(BaseModel):
    pergunta: str


class PerguntaResponse(BaseModel):
    resposta: str
    documentos_usados: list


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=PerguntaResponse)
def fazer_consulta(req: PerguntaRequest):
    resultado = query_rag(req.pergunta)
    return resultado


@app.post("/ingest")
def reindexar():
    """Endpoint para n8n ou triggers externos re-indexarem os dados."""
    ingest()
    return {"status": "ingestão concluída"}


# Serve o frontend
import os
_frontend_dir = "./frontend" if os.path.exists("./frontend") else "../frontend"
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
