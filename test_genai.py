import os
from google import genai
client = genai.Client()
for m in client.models.list():
    if "native-audio" in m.name or "2.5" in m.name:
        print(m.name)
