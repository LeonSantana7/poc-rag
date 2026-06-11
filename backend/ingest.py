import pandas as pd
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    # Cria a extensão antes de registrar o tipo
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    register_vector(conn)
    return conn


def row_to_text(row):
    status = "COM FALHA" if row["Machine failure"] == 1 else "NORMAL"
    tipos_falha = []
    if row["TWF"] == 1:
        tipos_falha.append("Desgaste de ferramenta (TWF)")
    if row["HDF"] == 1:
        tipos_falha.append("Dissipação de calor (HDF)")
    if row["PWF"] == 1:
        tipos_falha.append("Falha de potência (PWF)")
    if row["OSF"] == 1:
        tipos_falha.append("Sobrecarga (OSF)")
    if row["RNF"] == 1:
        tipos_falha.append("Falha aleatória (RNF)")

    falhas_str = ", ".join(tipos_falha) if tipos_falha else "Nenhuma"

    return (
        f"Produto {row['Product ID']} (Tipo {row['Type']}): "
        f"Temperatura do ar {row['Air temperature [K]']}K, "
        f"Temperatura do processo {row['Process temperature [K]']}K, "
        f"Velocidade rotacional {row['Rotational speed [rpm]']} RPM, "
        f"Torque {row['Torque [Nm]']} Nm, "
        f"Desgaste da ferramenta {row['Tool wear [min]']} min. "
        f"Status da máquina: {status}. "
        f"Tipos de falha detectados: {falhas_str}."
    )


def setup_db(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documentos (
                id SERIAL PRIMARY KEY,
                conteudo TEXT NOT NULL,
                embedding vector(384)
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_embedding
            ON documentos USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)
    conn.commit()
    print("Banco configurado.")


def ingest():
    print("Conectando ao PostgreSQL...")
    conn = get_conn()
    setup_db(conn)

    print("Carregando dataset...")
    df = pd.read_csv("/data/ai4i2020.csv")

    print("Carregando modelo de embeddings...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Limpa registros antigos para evitar duplicatas
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documentos;")
    conn.commit()
    print("Registros antigos removidos.")

    print(f"Indexando {len(df)} registros...")
    batch_size = 500

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        textos = [row_to_text(row) for _, row in batch.iterrows()]
        embeddings = model.encode(textos).tolist()

        with conn.cursor() as cur:
            for texto, embedding in zip(textos, embeddings):
                cur.execute(
                    "INSERT INTO documentos (conteudo, embedding) VALUES (%s, %s)",
                    (texto, embedding)
                )
        conn.commit()
        print(f"  {min(i + batch_size, len(df))}/{len(df)} registros indexados")

    conn.close()
    print("Ingestão concluída!")


if __name__ == "__main__":
    ingest()
