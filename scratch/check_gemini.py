import os
import google.generativeai as genai

def get_key():
    with open(".env", "r") as f:
        for line in f:
            if "GOOGLE_API_KEY" in line:
                return line.split("=")[1].strip()
    return None

key = get_key()
if not key:
    print("No key found")
    exit(1)

genai.configure(api_key=key)
print("Available models:")
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(m.name)
