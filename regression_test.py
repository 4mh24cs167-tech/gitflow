import httpx
import asyncio
import os
import json

async def run_regression():
    print("Starting regression tests...")
    
    # Need to get a token by mimicking the callback
    # For testing, we can just insert a user manually or use the register endpoint
    async with httpx.AsyncClient() as client:
        # Register a test user
        res = await client.post("http://localhost:8000/auth/register", json={
            "username": "tester1",
            "email": "tester1@test.com",
            "password": "password123"
        })
        print("Register:", res.status_code)
        
        # Login
        res = await client.post("http://localhost:8000/auth/login", data={
            "username": "tester1",
            "password": "password123"
        })
        token = res.json().get("access_token")
        print("Login:", res.status_code, "Token received:", bool(token))
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a repository
        res = await client.post("http://localhost:8000/repositories/", json={
            "name": "test-repo",
            "url": "https://github.com/octocat/Hello-World.git"
        }, headers=headers)
        print("Create Repo:", res.status_code)
        repo_id = res.json().get("id")
        
        # Trigger Scan
        res = await client.post(f"http://localhost:8000/repositories/{repo_id}/scan?commit_sha=HEAD", headers=headers)
        print("Trigger Scan:", res.status_code)
        
        # Wait a bit for background worker
        print("Waiting for scan to complete...")
        await asyncio.sleep(5)
        
        # Check Scans
        res = await client.get(f"http://localhost:8000/repositories/{repo_id}/scans", headers=headers)
        print("Get Scans:", res.status_code)
        scans = res.json()
        print(json.dumps(scans, indent=2))
        
        # Risk History
        res = await client.get(f"http://localhost:8000/repositories/{repo_id}/risk-history", headers=headers)
        print("Get Risk History:", res.status_code)
        print(json.dumps(res.json(), indent=2))
        
if __name__ == "__main__":
    asyncio.run(run_regression())
