from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import json
from pathlib import Path

from app.database import engine, SessionLocal, Base
from app.models import (
    Chat,
    Message,
    Document,
    DocumentChunk
)
from app.llm import stream_llm
from app.rag import (
    extract_text_from_pdf,
    split_text,
    create_embedding,
    cosine_similarity
)


RESOURCE_DIR = Path(
    os.environ.get(
        "MY_LOCAL_CHATGPT_RESOURCE_DIR",
        "."
    )
).resolve()


# =========================
# Database
# =========================

Base.metadata.create_all(bind=engine)


# =========================
# FastAPI
# =========================

app = FastAPI()


app.mount(
    "/static",
    StaticFiles(directory=str(RESOURCE_DIR / "static")),
    name="static"
)


# =========================
# Upload
# =========================

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# =========================
# Request Models
# =========================

class ChatRequest(BaseModel):
    message: str


class ChatTitleRequest(BaseModel):
    title: str


# =========================
# Home
# =========================

@app.get("/")
def home():
    return FileResponse(
        str(RESOURCE_DIR / "frontend" / "index.html")
    )


# =========================
# Chat List
# =========================

@app.get("/chats")
def get_chats():

    db = SessionLocal()

    chats = (
        db.query(Chat)
        .order_by(Chat.updated_at.desc())
        .all()
    )

    result = []

    for chat in chats:
        result.append({
            "id": chat.id,
            "title": chat.title
        })

    db.close()

    return result


# =========================
# Create Chat
# =========================

@app.post("/chats")
def create_chat():

    db = SessionLocal()

    chat = Chat(
        title="새 채팅"
    )

    db.add(chat)
    db.commit()
    db.refresh(chat)

    db.close()

    return {
        "id": chat.id,
        "title": chat.title
    }


# =========================
# Get Chat
# =========================

@app.get("/chats/{chat_id}")
def get_chat(chat_id: int):

    db = SessionLocal()

    messages = (
        db.query(Message)
        .filter(
            Message.chat_id == chat_id
        )
        .order_by(Message.created_at)
        .all()
    )

    result = []

    for message in messages:
        result.append({
            "role": message.role,
            "content": message.content
        })

    db.close()

    return result


# =========================
# Delete Chat
# =========================

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):

    db = SessionLocal()

    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id)
        .first()
    )

    if chat is None:

        db.close()

        return {
            "error": "Chat not found"
        }

    (
        db.query(Message)
        .filter(
            Message.chat_id == chat_id
        )
        .delete()
    )

    db.delete(chat)

    db.commit()
    db.close()

    return {
        "message": "Chat deleted"
    }


# =========================
# Rename Chat
# =========================

@app.put("/chats/{chat_id}")
def update_chat(
    chat_id: int,
    request: ChatTitleRequest
):

    db = SessionLocal()

    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id)
        .first()
    )

    if chat is None:

        db.close()

        return {
            "error": "Chat not found"
        }

    new_title = request.title.strip()

    if not new_title:

        db.close()

        return {
            "error": "Title cannot be empty"
        }

    chat.title = new_title[:100]

    db.commit()
    db.refresh(chat)

    db.close()

    return {
        "id": chat.id,
        "title": chat.title
    }


# =========================
# PDF Upload
# =========================

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    chat_id: int = Form(...)
):
    if not file.filename.lower().endswith(".pdf"):
        return {
            "error":
                "PDF 파일만 업로드할 수 있습니다."
        }

    if chat_id is None:
        return {
            "error":
                "채팅 ID가 필요합니다."
        }

    # =========================
    # PDF 저장
    # =========================

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        content = await file.read()
        buffer.write(content)

    # =========================
    # PDF 텍스트 추출
    # =========================

    text = extract_text_from_pdf(
        file_path
    )

    if not text.strip():
        return {
            "error":
                "PDF에서 텍스트를 추출할 수 없습니다."
        }

    # =========================
    # Document 저장
    # =========================

    db = SessionLocal()

    document = Document(
        chat_id=chat_id,
        filename=file.filename,
        text=text
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    document_id = document.id

    # =========================
    # Chunk 생성
    # =========================

    chunks = split_text(text)

    # =========================
    # Chunk + Embedding 저장
    # =========================

    for index, chunk in enumerate(chunks):

        embedding = create_embedding(chunk)

        chunk_data = DocumentChunk(
            document_id=document_id,
            chunk_index=index,
            content=chunk,
            embedding=json.dumps(
                embedding
            )
        )

        db.add(chunk_data)

    db.commit()

    db.close()

    return {
        "filename": file.filename,
        "document_id": document_id,
        "chunk_count": len(chunks),
        "text_length": len(text)
    }

# =========================
# Send Message
# =========================

@app.post(
    "/chats/{chat_id}/message"
)
def send_message(
    chat_id: int,
    request: ChatRequest
):

    db = SessionLocal()

    chat = (
        db.query(Chat)
        .filter(Chat.id == chat_id)
        .first()
    )

    if chat is None:

        db.close()

        return {
            "error": "Chat not found"
        }

    # =========================
    # 사용자 메시지 저장
    # =========================

    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=request.message
    )

    db.add(user_message)
    db.commit()

    # =========================
    # 채팅 제목 자동 생성
    # =========================

    if chat.title == "새 채팅":

        chat.title = request.message[:30]

    # =========================
    # 기존 대화 불러오기
    # =========================

    messages = (
        db.query(Message)
        .filter(
            Message.chat_id == chat_id
        )
        .order_by(Message.created_at)
        .all()
    )

    document_chunks = (
        db.query(DocumentChunk)
        .join(
            Document,
            Document.id == DocumentChunk.document_id
        )
        .filter(
            Document.chat_id == chat_id
        )
        .order_by(
            DocumentChunk.document_id,
            DocumentChunk.chunk_index
        )
        .all()
    )

    document_context = ""

    if document_chunks:
        summary_keywords = [
            "요약",
            "정리",
            "summarize",
            "summary"
        ]

        is_summary_request = any(
            keyword in request.message.lower()
            for keyword in summary_keywords
        )

        if is_summary_request:
            selected_chunks = document_chunks
        else:
            question_embedding = create_embedding(
                request.message
            )

            scored_chunks = []

            for chunk in document_chunks:
                chunk_embedding = json.loads(
                    chunk.embedding
                )

                scored_chunks.append((
                    cosine_similarity(
                        question_embedding,
                        chunk_embedding
                    ),
                    chunk
                ))

            scored_chunks.sort(
                key=lambda item: item[0],
                reverse=True
            )

            selected_chunks = [
                chunk
                for _, chunk in scored_chunks[:5]
            ]

        context_parts = []
        context_length = 0

        for chunk in selected_chunks:
            content = chunk.content.strip()

            if not content:
                continue

            if context_length + len(content) > 6000:
                break

            context_parts.append(content)
            context_length += len(content)

        if context_parts:
            document_context = (
                "아래는 사용자가 업로드한 PDF에서 가져온 "
                "참고 내용입니다. 답변할 때 이 내용을 우선 "
                "사용하세요.\n\n"
                "--- PDF 참고 내용 시작 ---\n"
                + "\n\n---\n\n".join(context_parts)
                + "\n--- PDF 참고 내용 끝 ---\n\n"
            )

    # =========================
    # Prompt 생성
    # =========================

    prompt = document_context

    for message in messages:

        if message.role == "user":

            prompt += (
                f"User: "
                f"{message.content}\n"
            )

        else:

            prompt += (
                f"Assistant: "
                f"{message.content}\n"
            )

    prompt += "Assistant:"

    # =========================
    # LLM Streaming
    # =========================

    def generate():

        answer = ""

        for token in stream_llm(prompt):

            answer += token

            yield token

        # =========================
        # Assistant 메시지 저장
        # =========================

        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=answer
        )

        db.add(
            assistant_message
        )

        chat.updated_at = (
            assistant_message.created_at
        )

        db.commit()
        db.close()

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )
