# Mifos AI Copilot Backend

This represents the **AI Middleware / Backend** that connects the official Mifos [web-app](https://github.com/openMF/web-app) to the [mcp-mifosx](https://github.com/mifos/mcp-mifosx) MCP Server. 

Because the `web-app` is a purely client-side Angular application, it cannot natively securely connect to PostgreSQL, run LLMs locally via Ollama, or spawn Python subprocesses via Stdio. This backend solves that.

## 🏗️ The 3-Tier AI Architecture

When a Teller opens the official Mifos Web App:

1. **Frontend (`openMF/web-app`)**: The Angular UI where the chat interface lives. When the teller types a message, the web-app sends an HTTP request to this backend.
2. **AI Backend (This Repo)**: A headless FastAPI server that:
   - Maintains chat history for the user in PostgreSQL.
   - Pings Ollama (Qwen) with the conversation history.
   - Spawns the MCP Server subprocess to get the 49 banking tools.
3. **Core Banking Layer (`mifos/mcp-mifosx`)**: The stateless integration layer that the backend pulls dynamically. It executes the tools against Fineract.

---

## 🚀 Deployment Guide (For Production Teams)

If your institution is deploying the Mifos Web App with the AI Assistant enabled, you must run this FastAPI backend alongside it.

### 1-Click Docker Deployment

The simplest way is to spin up the AI Backend environment via Docker. You do *not* need to explicitly clone the `mcp-mifosx` repo — Docker will do it for you automatically during the build!

**Requirements:**
- Docker and Docker Compose
- Ollama running (`ollama pull qwen2.5:7b`)

**Setup:**
```bash
git clone https://github.com/mifos/mifos-ai-client-backend.git
cd mifos-ai-client-backend
```

Configure your banking credentials:
```bash
cd backend
cp .env.example .env
nano .env
```
*(Point `MIFOSX_BASE_URL` to your live Apache Fineract instance).*

**Deploy the Backend ecosystem:**
```bash
cd ..
docker-compose up -d --build
```
> **What this does:**
> 1. Spins up a `mifos_ai_db` PostgreSQL container with persistent memory.
> 2. Builds the `mifos_ai_backend` container. During compilation, it automatically runs `git clone https://github.com/mifos/mcp-mifosx.git` inside the container.
> 3. Exposes the FastAPI endpoints securely on port `8000`.

### Connecting the `openMF/web-app`
Once the backend is running, log into your Mifos `web-app` codebase and configure the AI Assistant service to point requests to `http://your-server-ip:8000/api/chat`. The web app now has a fully functioning, context-aware AI Banking Assistant.


If you wish to run the components manually without Docker (e.g., for development):

### 1. Database
Run a local PostgreSQL instance (or use the provided `docker-compose.yml` in the `/backend` folder just for the DB).

### 2. Backend
```bash
# Clone the MCP Server first
git clone https://github.com/mifos/mcp-mifosx.git /path/to/mcp-mifosx

cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Update MCP_SERVER_PATH in .env to point to your clone
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Connecting the Frontend (in `openMF/web-app`)
You do not need to run any frontend code from this repository. 
Simply open your local checkout of `openMF/web-app`, configure its AI Assistant service to point its HTTP requests to `http://localhost:8000/api/chat`, and run `npm start` over there.
