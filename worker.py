import os
import time
import sqlite3
import docker
import psutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from eth_account.messages import encode_defunct
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from botchain.client import BotChain
from web3 import Web3

load_dotenv()

import json
from pathlib import Path
from eth_account import Account
Account.enable_unaudited_hdwallet_features()

START_TIME = time.time()
DB_PATH = os.path.expanduser("~/.autonome/execution_logs.db")
ESCROW_ADDRESS = "0x5b30dB9F00F9fa644a13117D5b31844223e3Fb4E"

def get_or_create_node_key() -> str:
    key_dir = Path.home() / ".autonome"
    key_dir.mkdir(parents=True, exist_ok=True)
    key_file = key_dir / "worker_key.json"
    
    if key_file.exists():
        with open(key_file, "r") as f:
            data = json.load(f)
            return data.get("private_key")
    else:
        acct, _ = Account.create_with_mnemonic()
        with open(key_file, "w") as f:
            json.dump({"private_key": acct.key.hex(), "address": acct.address}, f, indent=4)
        return acct.key.hex()

NODE_PRIVATE_KEY = get_or_create_node_key()

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
    conn.commit()
    conn.close()

init_db()

try:
    docker_client = docker.from_env()
except Exception as e:
    print(f"Warning: Could not connect to Docker daemon: {e}")
    docker_client = None

app = FastAPI(title="DePIN Docker Worker Node")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WorkloadManifest(BaseModel):
    task_id: str
    domain: str
    image: str
    env_vars: dict = {}
    operator_vault: str
    sub_agent: str

class VaultRequest(BaseModel):
    vault: str

CURRENT_VAULT = ""

class TaskResponse(BaseModel):
    task_id: str
    inference_result: str
    proof_hash: str
    signature: str
    sub_agent: str
    operator_vault: str

def execute_docker_sandbox(manifest: dict):
    try:
        if not NODE_PRIVATE_KEY:
            raise HTTPException(status_code=500, detail="NODE_PRIVATE_KEY not set in environment.")
        if not docker_client:
            raise HTTPException(status_code=500, detail="Docker client not initialized. Is the socket mounted?")

        actual_vault = CURRENT_VAULT or os.environ.get("OPERATOR_VAULT") or manifest.get("operator_vault", "")
        print(f"[Worker] Executing task {manifest["task_id"]}")
        print(f"[Worker] Operator Vault resolved to: {actual_vault}")

        # 1. Ephemeral Docker Execution
        try:
            raw_output = docker_client.containers.run(
                image=manifest["image"],
                environment=manifest.get("env_vars", {}),
                mem_limit="2g",
                detach=False,
                remove=True
            )
            output_str = raw_output.decode("utf-8").strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Docker execution failed: {str(e)}")

        # 2. Cryptographic Proof
        client = BotChain(private_key=NODE_PRIVATE_KEY, is_testnet=True)
        payload_str = f"{manifest["task_id"]}:{output_str}"
        proof_hash = client.w3.keccak(text=payload_str).hex()
        
        message = encode_defunct(text=proof_hash)
        signed_message = client.w3.eth.account.sign_message(message, private_key=NODE_PRIVATE_KEY)
        signature = signed_message.signature.hex()

        # 3. Persistence
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO execution_logs 
                (task_id, timestamp, domain, proof_hash, tx_hash, reward, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                manifest["task_id"],
                int(time.time()),
                manifest.get("domain", ""),
                proof_hash,
                "",
                "+1.5 ATMA", 
                "Executed"
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Worker] Warning: Error persisting logs: {e}")

        return dict(
            task_id=manifest["task_id"],
            inference_result=output_str,
            proof_hash=proof_hash,
            signature=signature,
            sub_agent=manifest.get("sub_agent", ""),
            operator_vault=actual_vault
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[Worker] Unhandled exception in execute_task: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal worker error: {str(e)}")


import asyncio
import requests

async def poll_for_tasks():
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8002")
    node_address = Web3().eth.account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else ""
    print(f"[Worker] Started Pull Polling Loop against {orchestrator_url}...")
    
    while True:
        try:
            vault = CURRENT_VAULT or os.environ.get("OPERATOR_VAULT", "")
            resp = requests.get(f"{orchestrator_url}/nodes/heartbeat?vault={vault}&node={node_address}", timeout=5)
            if resp.status_code == 200:
                task = resp.json()
                if task.get("status") != "idle":
                    print(f"[Worker] Received pulled task: {task.get('task_id')}")
                    
                    # 1. Execute Sandbox
                    result = execute_docker_sandbox(task)
                    
                    # 2. Post Proof to Orchestrator to trigger settlement
                    complete_resp = requests.post(f"{orchestrator_url}/tasks/complete", json=result, timeout=60)
                    if complete_resp.status_code == 200:
                        complete_data = complete_resp.json()
                        tx_hash = complete_data.get("tx_hash", "")
                        
                        # 3. Save Settlement Tx to local SQLite log
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE execution_logs SET tx_hash = ?, status = ? WHERE task_id = ?",
                                        (tx_hash, "Settled", task.get("task_id")))
                            conn.commit()
                            conn.close()
                            print(f"[Worker] Settlement success. Tx Hash updated: {tx_hash}")
                        except Exception as e:
                            print(f"[Worker] Failed to update local DB: {e}")
                    else:
                        print(f"[Worker] Orchestrator settlement failed: {complete_resp.text}")
        except requests.exceptions.RequestException:
            pass # Silent fail if orchestrator offline
        except Exception as e:
            print(f"[Worker] Polling loop error: {e}")
        
        await asyncio.sleep(3)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(poll_for_tasks())


@app.get("/logs")
def get_logs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM execution_logs ORDER BY timestamp DESC LIMIT 50")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"logs": rows}

class LogUpdate(BaseModel):
    tx_hash: str
    status: str = "Settled"

@app.patch("/logs/{task_id}")
def update_log(task_id: str, update: LogUpdate):
    """Called by the Orchestrator after on-chain settlement to write the real tx_hash."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE execution_logs SET tx_hash = ?, status = ? WHERE task_id = ?",
            (update.tx_hash, update.status, task_id)
        )
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found in logs.")
        print(f"[Worker] Updated log for task {task_id} with tx_hash {update.tx_hash}")
        return {"status": "updated", "task_id": task_id, "tx_hash": update.tx_hash}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update log: {str(e)}")

@app.post("/set_vault")
def set_vault(request: VaultRequest):
    global CURRENT_VAULT
    CURRENT_VAULT = request.vault
    return {"status": "success", "vault": CURRENT_VAULT}

@app.get("/status")
def get_node_status():
    cpu_percent = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    
    docker_online = False
    try:
        if docker_client:
            docker_client.ping()
            docker_online = True
    except Exception:
        docker_online = False

    process = psutil.Process()
    process_ram_mb = round(process.memory_info().rss / (1024 ** 2), 2)

    return {
        "status": "ONLINE" if docker_online else "DEGRADED",
        "uptime_seconds": int(time.time() - START_TIME),
        "node_address": Web3().eth.account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else None,
        "operator_vault_debug": CURRENT_VAULT or os.environ.get("OPERATOR_VAULT"),
        "hardware": {
            "cpu_usage_pct": cpu_percent,
            "ram_used_gb": round(ram.used / (1024 ** 3), 2),
            "ram_total_gb": round(ram.total / (1024 ** 3), 2),
            "ram_pct": ram.percent,
            "process_ram_mb": process_ram_mb
        },
        "engine": "docker",
        "network": {
            "chain_id": 968,
            "chain_name": "Bohr Testnet",
            "rpc": "https://rpc.bohr.life"
        }
    }
import signal

@app.post("/shutdown")
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return {"message": "Shutting down"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
