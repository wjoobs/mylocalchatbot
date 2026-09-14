from pypdf import PdfReader
import requests
import math


# =========================
# Ollama Embedding
# =========================

OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"


def create_embedding(text: str) -> list[float]:
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "input": text
        }
    )

    response.raise_for_status()

    data = response.json()

    return data["embeddings"][0]


# =========================
# PDF 텍스트 추출
# =========================

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


# =========================
# Chunking
# =========================

def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200
) -> list[str]:

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# =========================
# Cosine Similarity
# =========================

def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float]
) -> float:

    dot_product = sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (
        magnitude_a * magnitude_b
    )


# =========================
# 관련 Chunk 검색
# =========================

def search_chunks(
    text: str,
    question: str,
    top_k: int = 3
):
    chunks = split_text(text)

    if not chunks:
        return []

    chunk_embeddings = []

    for chunk in chunks:
        embedding = create_embedding(chunk)
        chunk_embeddings.append(embedding)

    question_embedding = create_embedding(
        question
    )

    results = []

    for i, embedding in enumerate(
        chunk_embeddings
    ):
        similarity = cosine_similarity(
            question_embedding,
            embedding
        )

        results.append({
            "chunk": chunks[i],
            "similarity": similarity
        })

    results.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    return results[:top_k]