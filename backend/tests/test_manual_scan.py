from fastapi.testclient import TestClient
from app.main import app
from app.api.routes.repositories import get_current_user
from app.database.models import User, Scan

client = TestClient(app)

async def mock_get_current_user():
    return User(id=1, username="test_user")

app.dependency_overrides[get_current_user] = mock_get_current_user

import unittest
from unittest.mock import AsyncMock, patch

class TestManualScanRoute(unittest.TestCase):
    @patch('app.api.routes.repositories.owned_repository', new_callable=AsyncMock)
    @patch('app.api.routes.repositories.queue_scan', new_callable=AsyncMock)
    def test_no_422(self, mock_queue, mock_owned):
        mock_queue.return_value = (Scan(id=1, status="QUEUED"), True)
        
        response = client.post("/repositories/3/scan", json={"commit_sha": "HEAD"})
        
        self.assertNotEqual(response.status_code, 422)
        self.assertEqual(response.status_code, 200)
