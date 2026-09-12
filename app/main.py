from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database import engine, SessionLocal, Base
from app.models import Chat, Message
from app.llm import stream_llm


Base.metadata.create_all(bind=engine)


app = FastAPI()


app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)


class ChatRequest(BaseModel):
    message: str


# =========================
# 홈페이지
# =========================

@app.get("/")
def home():

    return FileResponse(
        "frontend/index.html"
    )


# =========================
# 채팅 목록
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
# 새 채팅
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
# 특정 채팅의 메시지
# =========================

@app.get("/chats/{chat_id}")
def get_chat(chat_id: int):

    db = SessionLocal()

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
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

# 채팅 삭제
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


    # 해당 채팅의 메시지 삭제
    (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .delete()
    )


    # 채팅 삭제
    db.delete(chat)

    db.commit()

    db.close()


    return {
        "message": "Chat deleted"
    }

class ChatTitleRequest(BaseModel):
    title: str


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
# 메시지 전송
# =========================

@app.post("/chats/{chat_id}/message")
def send_message(
    chat_id: int,
    request: ChatRequest
):

    db = SessionLocal()


    # -------------------------
    # 채팅 찾기
    # -------------------------

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


    # -------------------------
    # 사용자 메시지 저장
    # -------------------------

    user_message = Message(
        chat_id=chat_id,
        role="user",
        content=request.message
    )

    db.add(user_message)

    db.commit()


    # -------------------------
    # 채팅 제목 설정
    # -------------------------

    if chat.title == "새 채팅":

        chat.title = request.message[:30]


    # -------------------------
    # 기존 대화 가져오기
    # -------------------------

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at)
        .all()
    )


    prompt = ""


    for message in messages:

        if message.role == "user":

            prompt += (
                f"User: {message.content}\n"
            )

        else:

            prompt += (
                f"Assistant: {message.content}\n"
            )


    prompt += "Assistant:"


    # -------------------------
    # Streaming
    # -------------------------

    def generate():

        answer = ""


        for token in stream_llm(prompt):

            answer += token

            yield token


        # -------------------------
        # AI 답변 저장
        # -------------------------

        assistant_message = Message(
            chat_id=chat_id,
            role="assistant",
            content=answer
        )

        db.add(assistant_message)

        chat.updated_at = assistant_message.created_at

        db.commit()

        db.close()


    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )