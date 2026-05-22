import requests

response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3.1",
        "messages": [
            {"role": "user", "content": "Explique o que é uma lei em 1 frase"}
        ],
        "stream": False
    }
)

print(response.json()["message"]["content"])