# MCP Server - Python Implementation

The **Mifos MCP Server** connects AI agents to your **Apache Fineract** banking backend. It is a standalone, universal integration tier that wraps the Fineract REST API into 49 typed tools.

---

## Architecture

This project implements a **Decoupled, API-First Architecture**. It establishes a deterministic, hallucination-free integration tier between any AI Agent and Apache Fineract.

```text
Apache Fineract / Mifos X
                 ↕
mcp_server.py (FastMCP) — Stateless MCP Server exposing 49 typed tools
                 ↕
========================= (MCP Standard Protocol Boundary) =========================
                 ↕
Local AI Agent (agent.py) — Reference client; runs locally and calls tools over stdio
```

The diagram above shows the minimal, decoupled flow: the AI agent never talks directly to Fineract — it calls a small set of typed tools exposed by `mcp_server.py`. This separation reduces hallucinations, enforces validation, and centralizes access control and logging.

## Folder Architecture

This folder contains the Python MCP Server implementation and supporting tools. Key files and directories:

- `.env` / `.env.example` — Environment variables for Fineract and Ollama configuration.
- `Dockerfile` — Image build for the MCP server.
- `agent.py` — Local AI agent frontend that talks to the MCP server over stdio (uses Ollama via LangChain).
- `mcp_server.py` — The standalone FastMCP server that registers and exposes the 49 MCP tools.
- `mcp_adapter.py` — Thin HTTP adapter for communicating with Apache Fineract (GET/POST/PUT/DELETE helpers).
- `requirements.txt` — Python dependencies for the MCP server.
- `tools/` — Domain tool implementations grouped by domain and helper registry:
    - `tools/mcp_adapter.py` — alternative adapter used by the tools (initialises `fineract_client`).
    - `tools/registry.py` — Domain router that selects subsets of tools for the LLM.
    - `tools/domains/clients.py` — Client-related tools (search, create, KYC identifiers).
    - `tools/domains/groups.py` — Group and Center management tools.
    - `tools/domains/loans.py` — Loan-related tools (create, repay, history).
    - `tools/domains/savings.py` — Savings account tools (deposit, withdraw, interest).
    - `tools/domains/staff.py` — Staff and Office management tools.
    - `tools/domains/accounting.py` — Chart of Accounts and Journal Entry tools.
- `core/` — Core server components and helpers used by the MCP runtime.
- `LICENSE` / `README.md` — Project license and documentation.

### Why this Architecture?
1. **Universal Reusability:** The MCP Server (`mcp_server.py`) is completely standalone. It does not contain any LLM logic. It can be paired with any local inference engine or agent framework.
2. **Anti-Hallucination Guardrails:** The server safely slims down verbose Fineract responses and pre-validates all IDs and statuses before executing dangerous mutations.
3. **Data Privacy & Sovereignty:** By connecting local Open-Source models (like Qwen 2.5 7B) directly to the MCP Server via Ollama, all sensitive banking data, PII, and financial records stay strictly within your local infrastructure. No data is sent to third-party AI providers or external APIs.
4. **Deterministic execution:** All banking actions are mapped to typed tools, ensuring the AI performs operations reliably without free-form hallucination of API calls.
5. **Conversational Memory:** The agent preserves short-term conversational context during an active session so the AI can follow multi-step prompts and refer to recent exchanges without re-querying tools repeatedly.

6. **Historical Context Memory:** The agent implements persistent historical memory backed by SQLite (default path: `~/.mifos/agent_memory.db`). This allows the agent to remember previous interactions, retain validated client and loan IDs, and resume multi-step workflows across sessions — improving efficiency and auditability.

Tellers can resume past conversations or start fresh threads instantly using the interactive agent frontend:

| Command | Action |
|---------|--------|
| Press Enter at startup | Start a new session |
| Paste a session ID | Resume a previous session |
| `new` (during chat) | Start a fresh thread |
| `id` (during chat) | Print current session ID |
| `quit` | Exit and save session |

---

## Quick Start

**1. Install requirements**
```bash
pip install -r requirements.txt
```

**2. Configure your Fineract connection** — copy `.env.example` to `.env`:
```ini
MIFOSX_BASE_URL=https://localhost:8443/fineract-provider/api/v1
MIFOSX_TENANT_ID=default
MIFOSX_USERNAME=mifos
MIFOSX_PASSWORD=password
```

**3. Test with the Reference Agent**
```bash
python agent.py
```

> **Note:** `agent.py` is a reference implementation. This server is designed to work with **any** MCP client, including Claude Code, n8n, or custom frontends.

> Requires [Ollama](https://ollama.com) with `qwen2.5:7b` for the reference agent.
> 
> To switch models, set `OLLAMA_MODEL=<model-name>` in your `.env` file (e.g. `llama3.1` or `qwen2.5:7b`).

---

## Available Tools (49)

The MCP server exposes 49 tools over the MCP boundary. They are grouped by domain below with the exact MCP tool names (these are the functions registered with `@mcp.tool()` in `mcp_server.py`).

- **Clients & Groups**
    - `search_clients` — Find client IDs by name.
    - `get_client` — Show key details for a specific client.
    - `get_client_accts` — Show all loans and savings accounts for a client.
    - `create_new_client` — Create a new client profile.
    - `activate_pending_client` — Activate a pending client.
    - `update_mobile` — Update a client's phone number.
    - `close_client_profile` — Close a client's profile.
    - `create_lending_group` — Create a lending group with members.
    - `get_group` — Show lending group details and members.
    - `get_identifiers` — List client ID documents (passports, etc.).
    - `add_identifier` — Add a new identity document for a client.
    - `list_documents` — List all uploaded files/documents for a client.
    - `list_client_charges` — List client-level fees or penalties.
    - `apply_fee` — Apply a one-time fee to a client.
    - `list_client_txns` — List financial transactions for the client.
    - `get_addresses` — Show client physical and mailing addresses.
    - `list_all_groups` — List all lending groups.
    - `activate_pending_group` — Activate a pending group.
    - `add_member_to_group` — Add a client member to a group.
    - `list_all_centers` — List all centers.
    - `get_center` — Show details for a center.
    - `create_new_center` — Create a new center.

- **Loans**
    - `get_loan` — Get key details for a specific loan.
    - `get_repayment_sched` — Get the repayment schedule for a loan.
    - `get_loan_hist` — Get the full transaction history for a loan.
    - `create_new_loan` — Create a new loan application (individual).
    - `approve_disburse_loan` — Approve and disburse a pending loan.
    - `reject_loan` — Reject a pending loan application.
    - `make_repayment` — Make a repayment on an active loan.
    - `apply_fee` — Apply a fee to a loan.
    - `waive_loan_interest` — Waive interest on a loan.
    - `get_overdue_loans_for_client` — List overdue/in-arrears loans for a client.
    - `create_group_loan_app` — Create a group loan application.

- **Savings**
    - `get_savings` — Get key details of a savings account.
    - `get_savings_txns` — Get transactions for a savings account.
    - `create_savings` — Create a new savings account.
    - `approve_activate_savings` — Approve and activate a savings account.
    - `close_savings` — Close a savings account.
    - `deposit` — Deposit money into a savings account.
    - `withdraw` — Withdraw money from a savings account.
    - `apply_savings_fee` — Apply a charge to a savings account.
    - `calc_post_interest` — Calculate and post interest to a savings account.

- **Staff & Offices**
    - `list_all_staff` — List bank staff members.
    - `get_staff` — Get details for a staff member.
    - `list_all_offices` — List all bank offices/branches.
    - `get_office` — Get details for an office.

- **Accounting**
    - `list_accounts` — List GL accounts (Chart of Accounts).
    - `list_journal_entries` — List journal entries.
    - `record_journal_entry` — Record a manual journal entry.

If you want these tool names exposed differently (shorter names or aliases), tell me which ones to change and I'll update `mcp_server.py` and the README accordingly.

---

## Development & Deployment

### Running the Banking Backend
This repository contains the **MCP Server** (the integration tier). To run the actual **Apache Fineract** banking engine, we recommend using the official community-maintained Docker configuration:

👉 **[Mifos X Platform - Docker Deployment](https://github.com/openMF/mifosx-platform)**

By using the official repository, you ensure you are always running the latest stable version of the banking engine with the most up-to-date security patches and data persistence practices.

### Building the MCP Server Image
If you wish to containerize the MCP server itself:
```bash
docker build -t mifos-mcp-server .
```

### Running the MCP Server
```bash
docker run -i --env-file .env mifos-mcp-server
```

---
