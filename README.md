# My Local AI chatbot
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
```

## Status
현재 개발 중입니다.
앞으로 RAG, Memory, Tool Calling 등의 기능을 공부하며 추가할 예정입니다.

## Desktop App 실행

개발 중에는 아래 명령으로 FastAPI 서버와 전용 앱 창을 함께 실행할 수 있습니다.

```bash
python app_launcher.py
```

Ollama와 `llama3.1:8b` 모델은 기존처럼 로컬에서 실행되어 있어야 합니다. 런처는 FastAPI 서버를 자동으로 띄운 뒤 브라우저 탭 대신 pywebview 앱 창을 엽니다.

## Windows EXE 빌드

의존성을 설치한 뒤 아래 명령으로 PyInstaller 빌드를 만들 수 있습니다.

```bash
pyinstaller --noconfirm --windowed --name "My Local ChatGPT" --add-data "frontend;frontend" --add-data "static;static" --add-data "app;app" --hidden-import webview.platforms.edgechromium app_launcher.py
```

빌드 결과는 `dist/My Local ChatGPT/` 안에 생성됩니다. `chat.db`와 `uploads/`는 실행 위치 기준으로 사용됩니다.

## Download
-> Latest Release