import psycopg2
import numpy as np
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Singletons
_model = None
_llm = None


def get_resources():
    global _model, _llm
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    if _llm is None:
        _llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.2,
        )
    return _model, _llm


def query_rag(pergunta: str, top_k: int = 5) -> dict:
    model, llm = get_resources()

    # 1. Vetorizar a pergunta (numpy array para pgvector)
    query_embedding = np.array(model.encode([pergunta])[0])

    # 2. Buscar documentos similares no pgvector
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT conteudo
            FROM documentos
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (query_embedding, top_k)
        )
        rows = cur.fetchall()
    conn.close()

    documentos = [row[0] for row in rows]
    contexto = "\n".join([f"- {doc}" for doc in documentos])

    # 3. Montar prompt
    system_prompt = """Você é um assistente especialista em manutenção preditiva industrial e OEE.
    Use os dados históricos fornecidos para responder de forma CONCISA e ESTRUTURADA.
    Regras:
    - Máximo 4 pontos ou parágrafos curtos
    - Use marcadores (- item) para listas
    - Use **negrito** para termos-chave
    - Vá direto ao ponto, sem introduções longas
    - Responda em português"""

    user_prompt = f"""Com base nos seguintes registros históricos de máquinas:

{contexto}

Responda a seguinte pergunta:
{pergunta}"""

    # 4. Gerar resposta com Groq
    mensagens = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    resposta = llm.invoke(mensagens)

    return {"resposta": resposta.content, "documentos_usados": documentos}
