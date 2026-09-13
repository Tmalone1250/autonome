import os
from dotenv import load_dotenv
import requests
import hashlib
import psutil
import time
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from eth_account.messages import encode_defunct

load_dotenv()
from web3.auto import w3
from settlement import execute_settlement

from fastapi.middleware.cors import CORSMiddleware

START_TIME = time.time()

DB_PATH = "execution_logs.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            task_id TEXT PRIMARY KEY,
            timestamp INTEGER,
            domain TEXT,
            proof_hash TEXT,
            tx_hash TEXT,
            reward TEXT,
            status TEXT
        )
    """)
    # Seed Initial Historic Logs
    cursor.execute("SELECT COUNT(*) FROM execution_logs")
    count = cursor.fetchone()[0]
    if count == 0:
        now = int(time.time())
        cursor.execute("""
            INSERT INTO execution_logs (task_id, timestamp, domain, proof_hash, tx_hash, reward, status)
            VALUES 
            (?, ?, ?, ?, ?, ?, ?),
            (?, ?, ?, ?, ?, ?, ?)
        """, (
            "task_0xbdex01", now - 600, "Web3 & DeFi", "4825c9bf6404d5213569de937c602de6967798083e8bc30aa2cd63b329912019", "0x13bd0cfc7005ba487e86b7ef149c6036e9b48c418729f856945ec9a3d36e2e78", "+1.5 ATMA", "Settled",
            "task_0xsmoke01", now - 1800, "Web3 & DeFi", "148053b45cad4a3bbace252b4758a2200c63ebcb359543800b06ad77579307f9", "0xdcc99bfa5991f1a03eec7287d16effb5e6d24ac1a5898c21fe892a20285e24ae", "+1.5 ATMA", "Settled"
        ))
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="DePIN Worker Node")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
NODE_PRIVATE_KEY = os.getenv("NODE_PRIVATE_KEY")

class TaskRequest(BaseModel):
    task_id: str
    prompt: str
    sub_agent_address: str
    domain: str = "General Utility"

class TaskResponse(BaseModel):
    task_id: str
    inference_result: str
    proof_hash: str
    signature: str
    settlement_tx_hash: str

@app.post("/task", response_model=TaskResponse)
def execute_task(req: TaskRequest):
    if not NODE_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="NODE_PRIVATE_KEY not set in environment.")

    # 1. Inference via Ollama
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3",
                "prompt": req.prompt,
                "stream": False,
                "keep_alive": "60s"
            },
            timeout=600
        )
        response.raise_for_status()
        inference_result = response.json().get("response", "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama inference failed: {str(e)}")

    # 2. Generate Cryptographic Proof
    payload_str = f"{req.task_id}:{req.prompt}:{inference_result}"
    proof_hash = hashlib.sha256(payload_str.encode()).hexdigest()
    
    # Sign the proof hash
    message = encode_defunct(text=proof_hash)
    signed_message = w3.eth.account.sign_message(message, private_key=NODE_PRIVATE_KEY)
    signature = signed_message.signature.hex()

    # 3. On-Chain Settlement
    try:
        tx_hash = execute_settlement(req.task_id, req.sub_agent_address, NODE_PRIVATE_KEY)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Settlement failed: {str(e)}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO execution_logs 
        (task_id, timestamp, domain, proof_hash, tx_hash, reward, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        req.task_id,
        int(time.time()),
        req.domain,
        proof_hash,
        tx_hash,
        "+1.5 ATMA", # For now, hardcode the worker's 15% cut of the 10 ATMA escrow
        "Settled"
    ))
    conn.commit()
    conn.close()

    return TaskResponse(
        task_id=req.task_id,
        inference_result=inference_result,
        proof_hash=proof_hash,
        signature=signature,
        settlement_tx_hash=tx_hash
    )

@app.get("/logs")
def get_logs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM execution_logs ORDER BY timestamp DESC LIMIT 50")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"logs": rows}

@app.post("/purge-memory")
def purge_memory():
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3",
                "keep_alive": 0
            },
            timeout=10
        )
        response.raise_for_status()
        return {"status": "success", "message": "Memory purged successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to purge memory: {str(e)}")

@app.get("/status")
def get_node_status():
    # Hardware Telemetry
    cpu_percent = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Check Ollama daemon connectivity
    ollama_online = False
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        ollama_online = (r.status_code == 200)
    except Exception:
        ollama_online = False

    process = psutil.Process()
    process_ram_mb = round(process.memory_info().rss / (1024 ** 2), 2)

    return {
        "status": "ONLINE" if ollama_online else "DEGRADED",
        "uptime_seconds": int(time.time() - START_TIME),
        "node_address": w3.eth.account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else None,
        "hardware": {
            "cpu_usage_pct": cpu_percent,
            "ram_used_gb": round(ram.used / (1024 ** 3), 2),
            "ram_total_gb": round(ram.total / (1024 ** 3), 2),
            "ram_pct": ram.percent,
            "disk_io_mb": 12, # Placeholder for container I/O
            "process_ram_mb": process_ram_mb
        },
        "model": "llama3",
        "network": {
            "chain_id": 968,
            "chain_name": "Bohr Testnet",
            "rpc": "https://rpc.bohr.life"
        }
    }
