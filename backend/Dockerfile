FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for asyncpg / psycopg2 if used)
RUN apt-get update && apt-get install -y gcc libpq-dev git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We clone the MCP Server dynamically during build so the backend container has access to it!
RUN git clone https://github.com/mifos/mcp-mifosx.git /opt/mcp-mifosx && \
    pip install -r /opt/mcp-mifosx/Python/MCP-Server-Python-Implementation/requirements.txt

COPY . .

EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
