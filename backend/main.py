from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import bcrypt
import jwt
import os
import datetime
import json
from db import get_db_pool, init_db
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretjwtkeythatshouldbechanged")
JWT_ALGORITHM = "HS256"

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Auth Dependencies
async def get_current_user(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

from fastapi import Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_authenticated_user_id(credentials: HTTPAuthorizationCredentials = Security(security)):
    return await get_current_user(credentials.credentials)

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    pool = await get_db_pool()
    await pool.close()

@app.post("/api/auth/signup")
async def signup(user: UserCreate):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        existing_user = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt).decode('utf-8')

        user_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id",
            user.email, hashed_password
        )

    token = jwt.encode(
        {"sub": str(user_id), "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/auth/login")
async def login(user: UserLogin):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        db_user = await conn.fetchrow("SELECT id, password_hash FROM users WHERE email = $1", user.email)

    if not db_user or not bcrypt.checkpw(user.password.encode('utf-8'), db_user['password_hash'].encode('utf-8')):
         raise HTTPException(status_code=401, detail="Invalid email or password")

    token = jwt.encode(
        {"sub": str(db_user['id']), "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )
    return {"access_token": token, "token_type": "bearer"}

# WebSocket and Analysis Endpoints
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, analysis_id: str):
        await websocket.accept()
        self.active_connections[analysis_id] = websocket

    def disconnect(self, analysis_id: str):
        if analysis_id in self.active_connections:
            del self.active_connections[analysis_id]

    async def send_message(self, message: str, analysis_id: str):
        if analysis_id in self.active_connections:
            await self.active_connections[analysis_id].send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/progress/{analysis_id}")
async def websocket_endpoint(websocket: WebSocket, analysis_id: str):
    await manager.connect(websocket, analysis_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(analysis_id)

from azure_scanner import get_resource_groups, get_resources_in_group

@app.get("/api/resource-groups")
async def fetch_resource_groups(user_id: str = Depends(get_authenticated_user_id)):
    try:
        rgs = get_resource_groups()
        return [rg.get("name") for rg in rgs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel
import asyncio
import uuid
from ai_analyzer import analyze_costs

class AnalyzeRequest(BaseModel):
    resource_group: str

@app.post("/api/analyze")
async def run_analysis(request: AnalyzeRequest, user_id: str = Depends(get_authenticated_user_id)):
    analysis_id = str(uuid.uuid4())
    pool = await get_db_pool()

    async def process_analysis():
        try:
            await asyncio.sleep(1) # Small delay to allow client to connect to ws

            await manager.send_message("Fetching resource groups...", analysis_id)
            await asyncio.sleep(1)

            await manager.send_message(f"Scanning resources in {request.resource_group}...", analysis_id)
            resources = get_resources_in_group(request.resource_group)

            await manager.send_message("Analyzing costs with AI...", analysis_id)
            analysis_result = await analyze_costs(resources)

            await manager.send_message("Storing results...", analysis_id)
            async with pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO analyses (user_id, resource_group, resources_scanned, issues_found, estimated_savings, analysis_result, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', int(user_id), request.resource_group, len(resources), analysis_result.get("issues_count", 0),
                    analysis_result.get("estimated_savings", "$0"), json.dumps(analysis_result), "completed"
                )
            await manager.send_message("Analysis complete", analysis_id)
        except Exception as e:
            await manager.send_message(f"Error: {str(e)}", analysis_id)
        finally:
            pass  # pool stays open for app lifetime

    # Run the background task (in real app we might use BackgroundTasks or Celery, here we use asyncio.create_task for simplicity with WS)
    asyncio.create_task(process_analysis())

    return {"analysis_id": analysis_id, "status": "started"}

@app.get("/api/history")
async def get_history(user_id: str = Depends(get_authenticated_user_id)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        records = await conn.fetch('''
            SELECT id, resource_group, resources_scanned, issues_found, estimated_savings, created_at, analysis_result
            FROM analyses
            WHERE user_id = $1
            ORDER BY created_at DESC
        ''', int(user_id))

    history = []
    for r in records:
        history.append({
            "id": r["id"],
            "resource_group": r["resource_group"],
            "resources_scanned": r["resources_scanned"],
            "issues_found": r["issues_found"],
            "estimated_savings": r["estimated_savings"],
            "created_at": r["created_at"].isoformat(),
            "analysis_result": json.loads(r["analysis_result"]) if r["analysis_result"] else None
        })
    return history

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
