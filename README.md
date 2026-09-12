#My Local AI chatbot
Ollama와 Llama 3.1 8B를 이용해 만든 로컬 AI 채팅 웹앱입니다.

## Tech Stack
- Python
- FastAPI
- SQLite
- SQLAlchemy
- Llama 3.1 8B
- HTML/CSS/Javascript

## Features
- 로컬 LLM 채팅
- 실시간 응답 Streaming
- 채팅 기록 저장
- 채팅 생성/삭제/불러오기
- 채팅 제목 수정
- Markdown 렌더링
- AI 답변 복사

## Project Structure
```text
my-local-chatgpt/
├── app/
│   ├── main.py
│   ├── llm.py
│   ├── database.py
│   └── models.py
├── frontend/
│   └── index.html
├── static/
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md

## Status
현재 개발 중입니다.
앞으로 RAG, Memory, Tool Calling 등의 기능을 공부하며 추가할 예정입니다.