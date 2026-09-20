import os
from dotenv import load_dotenv; load_dotenv('.env')
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
res = client.post("/chat", json={"prompt": "hi"})
print("STATUS:", res.status_code)
print("BODY:", res.text)
