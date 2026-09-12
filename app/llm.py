import requests
import json


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.1:8b"


def ask_llm(prompt: str) -> str:

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
        },
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]


def stream_llm(prompt: str):

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": True,
        },
        stream=True,
    )

    response.raise_for_status()


    for line in response.iter_lines():

        if line:

            data = json.loads(line)

            yield data["response"]