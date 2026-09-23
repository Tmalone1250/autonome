import os
import time
import sqlite3
import docker
import psutil
import hashlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from eth_account.messages import encode_defunct
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from botchain.client import BotChain
import os
from pathlib import Path
env_path = Path.home() / ".autonome" / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv() # Fallback to current directory

import json
from pathlib import Path
from eth_account import Account
Account.enable_unaudited_hdwallet_features()

START_TIME = time.time()
DB_PATH = os.path.expanduser("~/.autonome/execution_logs.db")
ESCROW_ADDRESS = "0xF54eA7205dc77C02FdCf86c4707f7cF7BDB3C372"

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

GLOBAL_ACU_SCORE = 0

def run_acu_benchmark():
    global GLOBAL_ACU_SCORE
    print("[Worker] Running ACU Boot Benchmark (5s CPU lock)...")
    start = time.time()
    iterations = 0
    data = b"autonome_acu_benchmark"
    while time.time() - start < 5.0:
        data = hashlib.sha256(data).digest()
        iterations += 1
    
    # 10,000 hashes = 1 ACU
    GLOBAL_ACU_SCORE = max(1, iterations // 10000)
    print(f"[Worker] ACU Benchmark complete. Score: {GLOBAL_ACU_SCORE} ACU ({iterations} iterations)")

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
    sub_agent: str

class VaultRequest(BaseModel):
    vault: str

class TaskResponse(BaseModel):
    task_id: str
    inference_result: str
    proof_hash: str
    signature: str
    sub_agent: str

def execute_docker_sandbox(manifest: dict):
    try:
        if not NODE_PRIVATE_KEY:
            raise HTTPException(status_code=500, detail="NODE_PRIVATE_KEY not set in environment.")
        if not docker_client:
            raise HTTPException(status_code=500, detail="Docker client not initialized. Is the socket mounted?")

        # Vault is resolved dynamically by Relayer
        print(f"[Worker] Executing task {manifest.get('task_id', '')}")

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
        payload_str = f"{manifest.get('task_id', '')}:{output_str}"
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
                "PENDING",
                "+1.5 ATMA", 
                "Executed"
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Worker] Warning: Error persisting logs: {e}")

        node_address = Account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else ""
        return dict(
            task_id=manifest["task_id"],
            inference_result=output_str,
            proof_hash=proof_hash,
            signature="",
            sub_agent=manifest.get("sub_agent", ""),
            node_address=node_address
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[Worker] Unhandled exception in execute_task: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal worker error: {str(e)}")


import asyncio
import requests
import traceback

async def execute_and_report(task: dict):
    """
    Execute a task in a thread pool (non-blocking) then send the signed
    proof back to the Orchestrator over HTTP.
    """
    loop = asyncio.get_event_loop()
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8002")
    try:
        result = await loop.run_in_executor(None, execute_docker_sandbox, task)
        # HTTP POST to /tasks/complete
        resp = requests.post(f"{orchestrator_url}/tasks/complete", json=result, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[Worker] ✅ Proof submitted for task {task.get('task_id')}")
            # Update local log with tx_hash
            tx_hash = data.get("tx_hash", "")
            error = data.get("error", "")
            final_status = "Queued for Settlement" if tx_hash == "PENDING" else ("Settled" if not error else "Failed")
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE execution_logs SET tx_hash = ?, status = ? WHERE task_id = ?",
                    (tx_hash, final_status, task.get("task_id", "")),
                )
                conn.commit()
                conn.close()
                print(f"[Worker] Task result submitted. On-chain settlement is {final_status}.")
            except Exception as e:
                print(f"[Worker] Failed to update local DB: {e}")
        else:
            print(f"[Worker] Failed to submit proof. Orchestrator returned {resp.status_code}")
    except Exception as e:
        print(f"[Worker] execute_and_report error: {e}")
        # Send an error proof
        try:
            node_address = Account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else ""
            error_payload = {
                "task_id":          task.get("task_id", ""),
                "inference_result": f"Error: {str(e)}",
                "proof_hash":       "",
                "signature":        "",
                "sub_agent":        task.get("sub_agent", ""),
                "node_address":     node_address,
            }
            requests.post(f"{orchestrator_url}/tasks/complete", json=error_payload, timeout=10)
        except Exception:
            pass


async def http_polling_loop():
    """
    Persistent HTTP polling loop (3s) replacing WebSockets.
    """
    orchestrator_url = os.environ.get("ORCHESTRATOR_URL", "http://127.0.0.1:8002")
    node_address = Account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else ""

    print(f"[Worker] Starting HTTP Polling Loop to {orchestrator_url}/nodes/heartbeat")
    
    while True:
        try:
            hw = get_node_status().get("hardware", {})
            payload = {
                "node_id": node_address,
                "hardware": hw,
                "max_acus": GLOBAL_ACU_SCORE
            }
            
            resp = requests.post(f"{orchestrator_url}/nodes/heartbeat", json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "task":
                    task_data = data.get("task", {})
                    print(f"[Worker] ⚡ Task received via HTTP: {task_data.get('task_id')}")
                    asyncio.create_task(execute_and_report(task_data))
            
            # Sync PENDING logs from Orchestrator
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT task_id FROM execution_logs WHERE tx_hash IN ('', 'PENDING', 'Pending...')")
                pending_tasks = cursor.fetchall()
                for row in pending_tasks:
                    t_id = row['task_id']
                    status_resp = requests.get(f"{orchestrator_url}/tasks/status/{t_id}", timeout=5)
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        if status_data.get("status") == "completed":
                            res_dict = status_data.get("result", {})
                            real_tx = res_dict.get("settlement_tx_hash", "PENDING")
                            err = res_dict.get("error", "")
                            if err:
                                real_tx = "Failed"
                            if real_tx not in ("PENDING", "Pending...") or err:
                                final_status = "Settled" if not err else "Failed"
                                cursor.execute(
                                    "UPDATE execution_logs SET tx_hash = ?, status = ? WHERE task_id = ?",
                                    (real_tx, final_status, t_id)
                                )
                                conn.commit()
                        elif status_data.get("status") == "pending":
                            # Check if the task is a ghost task from legacy WS
                            cursor.execute("SELECT timestamp FROM execution_logs WHERE task_id = ?", (t_id,))
                            ts_row = cursor.fetchone()
                            if ts_row and (time.time() - ts_row['timestamp']) > 300:
                                cursor.execute(
                                    "UPDATE execution_logs SET tx_hash = ?, status = ? WHERE task_id = ?",
                                    ("Failed", "Failed", t_id)
                                )
                                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Worker] Error syncing pending logs: {e}")

        except requests.exceptions.RequestException as e:
            print(f"[Worker] Heartbeat failed: {e}")
        except Exception as e:
            print(f"[Worker] Unexpected error in polling loop: {e}")
            traceback.print_exc()

        await asyncio.sleep(3)


@app.on_event("startup")
async def startup_event():
    node_address = Account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else ""
    print("\n" + "="*70)
    print(f"[ACTION REQUIRED] Register this Node Address in your Dashboard:")
    print(f" -> {node_address}")
    print("="*70 + "\n")
    
    # Run the CPU-locking benchmark in a thread pool to avoid freezing the event loop completely
    await asyncio.get_event_loop().run_in_executor(None, run_acu_benchmark)
    asyncio.create_task(http_polling_loop())


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
        "node_address": Account.from_key(NODE_PRIVATE_KEY).address if NODE_PRIVATE_KEY else None,
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
