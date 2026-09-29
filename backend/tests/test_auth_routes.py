from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_missing_auth():
    response = client.get("/repositories/")
    assert response.status_code == 401
    
def test_invalid_auth():
    response = client.get("/repositories/", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_invalid_ask_auth():
    response = client.post("/repositories/1/scans/1/ask", json={"question": "What changed?"}, headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_missing_ask_auth():
    response = client.post("/repositories/1/scans/1/ask", json={"question": "What changed?"})
    assert response.status_code == 401
