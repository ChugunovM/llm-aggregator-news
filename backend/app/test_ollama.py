import requests
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

try:
    resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    if resp.status_code == 200:
        models = [m["name"] for m in resp.json().get("models", [])]
        print("Ollama доступен")
        print("Доступные модели:", models)
    else:
        print("Ollama вернул ошибку:", resp.status_code, resp.text)
except Exception as e:
    print("Не удалосб подключиться к Ollama:", e)