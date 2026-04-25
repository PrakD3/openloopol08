import os
import httpx

def get_key():
    with open(".env", "r") as f:
        for line in f:
            if "GROQ_API_KEY" in line:
                return line.split("=")[1].strip()
    return None

key = get_key()
if not key:
    print("No key found")
    exit(1)

response = httpx.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {key}"}
)
data = response.json()
models = [m["id"] for m in data["data"]]
print("\n".join(models))
