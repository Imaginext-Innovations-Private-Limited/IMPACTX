import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi.testclient import TestClient
from main import app

print("Creating TestClient...")
with TestClient(app) as client:
    print("Testing GET /api/health...")
    r = client.get("/api/health")
    print("Result:", r.status_code, r.json())
