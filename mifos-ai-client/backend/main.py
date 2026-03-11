"""
Mifos AI Web Client — FastAPI Backend

This backend replicates the logic of `agent.py` but exposes it as a REST API.
It connects to the Mifos MCP Server via stdio, uses Qwen via Ollama,
and persists conversation history in PostgreSQL.
"""
import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────
MODEL_NAME      = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
# Path relative to the client backend pointing to the MCP Server
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "../../Python/MCP-Server-Python-Implementation/mcp_server.py")
DATABASE_URL    = os.getenv("DATABASE_URL", "postgresql://mifos:password@localhost:5432/mifos_chat")

SYSTEM_PROMPT = """You are a Banking Assistant for Mifos X with persistent memory. You have access to tools that talk to a live banking database.

CRITICAL RULES — NEVER BREAK THESE:

1. TOOLS ONLY: Execute every request by calling a tool. NEVER output JSON blocks, code, or text descriptions of what you plan to do. If you cannot find a tool, say so. Otherwise, call it immediately.

2. NO GUESSED IDs: You are FORBIDDEN from using any numeric ID you did not receive from a tool response in this conversation. IDs like 12345, 999, or 0 are HALLUCINATIONS. If you do not have the ID, SEARCH FOR IT FIRST.

3. MANDATORY LOOKUP CHAIN — Follow this exact order whenever a name is given:
   Step 1: Call search_clients(name) to find the client ID.
   Step 2: Call get_client_accts(client_id) to find loan/savings account IDs.
   Step 3: Call the requested tool with the ID from Step 2.
   DO NOT skip steps. DO NOT guess the ID.

4. FACTS ONLY: Only report values that were explicitly returned by a tool. Never infer, assume, or invent dates, amounts, or IDs not present in the tool response.

5. MEMORY: Reuse IDs already established earlier in this conversation. If a client or loan was already looked up, use that ID directly without searching again.

6. ONE TOOL AT A TIME: Call ONE tool, wait for its result, then call the next. NEVER write pseudo-code like search_clients(name)["id"] or chain calls in text.

7. COMPLETE LISTS: When a tool returns a list (loans, accounts, transactions), report EVERY item. Never summarise or truncate.

8. ALWAYS REPORT CLIENT ID: When search_clients returns a result, always state the client's full name and clientId at the start of your response.
"""

# ─── LLM (Qwen via Ollama) ────────────────────────────────────────────────────
llm = ChatOllama(
    model=MODEL_NAME,
    temperature=0,
    num_ctx=4096,
    num_predict=1024,
    repeat_penalty=1.0,
    num_gpu=20,
)

# ─── Global State ─────────────────────────────────────────────────────────────
db_pool: asyncpg.Pool = None
mcp_tools: list = []


# ─── Database Functions (PostgreSQL) ──────────────────────────────────────────
async def init_db(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                created_at   TIMESTAMPTZ DEFAULT NOW(),
                last_active  TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS messages (
                id           SERIAL PRIMARY KEY,
                session_id   TEXT REFERENCES sessions(session_id),
                role         TEXT NOT NULL,
                content      TEXT NOT NULL,
                created_at   TIMESTAMPTZ DEFAULT NOW()
            );
        """)

async def load_history(pool: asyncpg.Pool, session_id: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content FROM messages WHERE session_id=$1 ORDER BY created_at ASC",
            session_id
        )
        return [{"role": r["role"], "content": r["content"]} for r in rows]

async def save_message(pool: asyncpg.Pool, session_id: str, role: str, content: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES ($1, $2, $3)",
            session_id, role, content
        )
        await conn.execute(
            "UPDATE sessions SET last_active=NOW() WHERE session_id=$1",
            session_id
        )

async def ensure_session(pool: asyncpg.Pool, session_id: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sessions (session_id) VALUES ($1) ON CONFLICT DO NOTHING",
            session_id
        )


# ─── App Lifecycle ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, mcp_tools

    # 1. Connect to PostgreSQL
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        await init_db(db_pool)
        print("✅ PostgreSQL connected and initialized schemas")
    except Exception as e:
        print(f"❌ DB Error: {e} (Ensure PostgreSQL is running)")

    # 2. Connect to MCP Server via stdio
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[MCP_SERVER_PATH],
    )
    # Note: the stdio_client keeps a persistent subprocess open for the server lifespan
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await load_mcp_tools(session)
            print(f"✅ Loaded {len(mcp_tools)} MCP tools from server")
            
            # Yield control to FastAPI while keeping the subprocess Alive
            yield

    if db_pool:
        await db_pool.close()


app = FastAPI(title="Mifos AI Web Client Backend", lifespan=lifespan)

# Allow the Angular frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── API Routes ───────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str

@app.post("/api/sessions")
async def create_session():
    """Create a new chat session."""
    session_id = f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    await ensure_session(db_pool, session_id)
    return {"session_id": session_id}

@app.get("/api/sessions/{session_id}/history")
async def get_history(session_id: str):
    """Load full conversation history for a session."""
    history = await load_history(db_pool, session_id)
    return {"session_id": session_id, "messages": history}

@app.get("/api/sessions")
async def list_sessions():
    """List all available sessions for resuming."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT session_id, last_active FROM sessions ORDER BY last_active DESC LIMIT 20"
        )
        return {"sessions": [{"session_id": r["session_id"], "last_active": str(r["last_active"])} for r in rows]}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message and get a reply from the Mifos AI Agent (Stateless endpoint)."""
    await ensure_session(db_pool, req.session_id)

    # 1. Load full conversation history from PostgreSQL
    history = await load_history(db_pool, req.session_id)

    # 2. Build LangChain message history
    lc_messages = [(msg["role"], msg["content"]) for msg in history]
    lc_messages.append(("human", req.message))

    # 3. Save the new user message to DB
    await save_message(db_pool, req.session_id, "human", req.message)

    # 4. Run LangGraph ReAct agent
    # Because we inject full history, the LLM "remembers" context
    agent = create_react_agent(llm, mcp_tools, prompt=SYSTEM_PROMPT)

    reply = ""
    async for chunk in agent.astream(
        {"messages": lc_messages},
        stream_mode="values"
    ):
        message = chunk["messages"][-1]
        
        # Capture final AI text response
        if message.type == "ai" and not getattr(message, "tool_calls", []) and message.content:
            reply = message.content

    if not reply:
        raise HTTPException(status_code=500, detail="Agent returned no response.")

    # 5. Save the final assistant reply to DB
    await save_message(db_pool, req.session_id, "assistant", reply)

    return ChatResponse(session_id=req.session_id, reply=reply)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
